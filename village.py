import time
from google import genai
from google.genai import types
from google.genai.errors import ClientError
import os
import sys
import json
from pathlib import Path
import asyncio
import argparse

import system_prompt
import tools
import tasks
import ui

MODELS = ("gemini-2.5-pro", "gemini-2.5-flash")


def get_api_key() -> str | None:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    cwd = Path.cwd()
    for dir in [cwd, *cwd.parents]:
        env_file = dir / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None


api_key = get_api_key()
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

client = genai.Client(api_key=api_key)


def remove_thought(o):
    """Remove binary thought signatures so we can easily turn this into json."""
    if isinstance(o, dict):
        return {
            k: remove_thought(v) for (k, v) in o.items() if k != "thought_signature"
        }
    if isinstance(o, list):
        return [remove_thought(v) for v in o]
    return o


class TaskRunner:
    def __init__(self, args: argparse.Namespace):
        self.output = args.output
        self.temperature = args.temperature
        self.model = args.model
        self.task = tasks.get_task(args.task, args)
        config = types.GenerateContentConfig(
            tools=self.task.tools,
            system_instruction=system_prompt.SYSTEM_PROMPT,
            temperature=self.temperature,
        )

        config.automatic_function_calling = types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=1
        )
        self.chat = client.aio.chats.create(model=self.model, config=config)
        tools.on_failure = lambda msg: self.task_failure(msg)
        tools.on_success = lambda msg: self.task_success(msg)
        self.completed = False
        self.successful = None
        self.usage_metadata = None
        self.start_time = None
        self.duration = None

    async def send_message(self, prompt: str | None = None) -> None:
        while not self.completed:
            try:
                response = await self.chat.send_message(prompt or "")
                if response.usage_metadata:
                    self.usage_metadata = response.usage_metadata.model_dump()

                if response.candidates is None or len(response.candidates) != 1:
                    from pdb import set_trace

                    set_trace()
                else:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.text:
                                print(
                                    f"FROM MODEL: {part.text.replace('\n', '\nFROM MODEL: ')}"
                                )
                    else:
                        if candidate.finish_reason == types.FinishReason.RECITATION:
                            self.task_failure(
                                f"Model ended up failing with: {candidate}"
                            )
                        else:
                            print("WARNING, MODEL RETURNED: {candidate}")
                break
            except ClientError as err:
                # TODO: implement better back-off
                print("Got {err}, sleeping 30s and retrying...")
                await asyncio.sleep(30)

    async def run(self):
        self.start_time = time.time()
        await self.send_message(self.task.prompt)
        while not self.completed:
            self.save_state()
            await self.send_message()

    def get_history(self):
        return [remove_thought(h.model_dump()) for h in self.chat.get_history()]

    def save_state(self):
        if self.output:
            with open(self.output, "wt") as h:
                json.dump(self.get_state(), h, indent=2)
        else:
            print("not saving state.")

    def get_state(self):
        return {
            "history": self.get_history(),
            "model": self.model,
            "task": self.task.NAME,
            "task_prompt": self.task.prompt,
            "temperature": self.temperature,
            "usage": self.usage_metadata,
            "completed": self.completed,
            "successful": self.successful,
            "duration": self.duration or time.time() - (self.start_time or 0),
        }

    def task_success(self, message: str):
        print(f"TASK SUCCESS: {message}")
        self.duration = time.time() - (self.start_time or 0)
        self.completed = True
        self.successful = True
        self.save_state()

    def task_failure(self, message):
        print(f"TASK FAILURE: {message}")
        self.duration = time.time() - (self.start_time or 0)
        self.completed = True
        self.successful = False
        self.save_state()


async def run_task(args: argparse.Namespace):
    task_runner = TaskRunner(args)
    webui = None
    if args.ui:
        webui = ui.UI(lambda: task_runner.get_state())
        await webui.start()
    await task_runner.run()
    if webui is not None:
        await webui.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Village: keeping agents locked down.")
    subcommands = parser.add_subparsers(
        dest="subcommand", help="Sub-command to use", metavar="COMMAND"
    )

    # Run command
    run_parser = subcommands.add_parser("run", help="Run a task.")
    run_parser.add_argument(
        "--model",
        type=str,
        default=MODELS[0],
        choices=MODELS,
        help="The LLM model to use.",
    )
    run_parser.add_argument(
        "--temperature",
        type=float,
        default=1,
        help="The LLM temperature. Defaults to 1. Range is 0 to 2. "
        + "Lower values are less random, Higher values are more random.",
    )
    run_parser.add_argument(
        "--output", type=Path, help="Where to put the JSON recording of the sessions."
    )
    run_parser.add_argument(
        "--ui", action="store_true", help="Run the web UI while the task runs"
    )
    tasks.add_task_parsers(run_parser)

    # View command
    view_parser = subcommands.add_parser("view", help="View a task recording.")
    view_parser.add_argument("recording", type=Path, help="The recording to view.")

    # Parse and dispatch to subcommands
    args = parser.parse_args()

    if args.subcommand == "run":
        asyncio.run(run_task(args))
    elif args.subcommand == "view":
        webui = ui.UI(lambda: json.load(open(args.output)))
        webui.run_forever()
    else:
        raise Exception(f"Unknown subcommand: {args.subcommand}")
