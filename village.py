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
    if isinstance(o, dict):
        return {
            k: remove_thought(v) for (k, v) in o.items() if k != "thought_signature"
        }
    if isinstance(o, list):
        return [remove_thought(v) for v in o]
    return o


class TaskRunner:
    def __init__(self, task: tasks._BaseTask, model: str):
        self.task = task
        self.model = model
        config = types.GenerateContentConfig(
            tools=task.tools,
            system_instruction=system_prompt.SYSTEM_PROMPT,
            # temperature=0,
        )

        config.automatic_function_calling = types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=1  # 0  # 000
        )
        self.chat = client.aio.chats.create(model=model, config=config)
        tools.on_failure = lambda msg: self.task_failure(msg)
        tools.on_success = lambda msg: self.task_success(msg)
        self.completed = False
        self.successful = None

    async def send_message(self, prompt: str | None = None):
        while not self.completed:
            try:
                response = await self.chat.send_message(prompt or "")
                return response.text
            except ClientError as err:
                # TODO: implement better back-off
                print("Got {err}, sleeping 30s and retrying...")
                await asyncio.sleep(30)

    async def run(self):
        await self.send_message(self.task.prompt)
        while not self.completed:
            self.save_history()
            await self.send_message()

    def get_history(self):
        return [remove_thought(h.model_dump()) for h in self.chat.get_history()]

    def save_history(self):
        with open("village_history.json", "wt") as h:
            json.dump(self.get_history(), h, indent=2)

    def task_success(self, message: str):
        print(f"TASK SUCCESS: {message}")
        self.save_history()
        self.completed = True
        self.successful = True

    def task_failure(self, message):
        print(f"TASK FAILURE: {message}")
        self.save_history()
        self.completed = True
        self.successful = False


async def main(task: tasks._BaseTask, model: str):
    task_runner = TaskRunner(task, model)
    webui = ui.UI(lambda: task_runner.get_history())

    await webui.start()

    await task_runner.run()
    await webui.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Village agent.")
    parser.add_argument("--model", type=str, default=MODELS[0], choices=MODELS)
    tasks.add_task_parsers(parser)
    args = parser.parse_args()
    print(repr(args))

    if args.task:
        task = tasks.get_task(args.task, args)
        if task is None:
            print(f"Unknown task: {args.task}")
            sys.exit(1)
        asyncio.run(main(task, args.model))
    else:
        print("hey, you need to specify a task")
