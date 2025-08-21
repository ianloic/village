from google import genai
import os
import json
from pathlib import Path
import asyncio
import argparse

import tasks
import ui
import summarize
from task_runner import TaskRunner, MODELS


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

    # Summarize command
    summarize.add_subcommand(subcommands)

    # Parse and dispatch to subcommands
    args = parser.parse_args()

    if args.subcommand == "run":
        asyncio.run(run_task(args))
    elif args.subcommand == "view":
        webui = ui.UI(lambda: json.load(open(args.output)))
        webui.run_forever()
    elif args.subcommand == "summarize":
        summarize.summarize_command(args)
    else:
        parser.print_help()
        exit(1)
