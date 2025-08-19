import argparse
import tasks.hlcpp_migration
from tasks.base_task import _BaseTask

TASKS = [tasks.hlcpp_migration.HlcppMigration]


def add_task_parsers(parser: argparse.ArgumentParser):
    """Adds argument parsers for all available tasks."""
    subparsers = parser.add_subparsers(dest="task", help="Tasks to run", metavar="TASK")
    for task in TASKS:
        task_name = task.NAME
        task_parser = subparsers.add_parser(task_name, help=task.__doc__)
        task.register_arguments(task_parser)
    return subparsers


def get_task(name: str, args: argparse.Namespace) -> _BaseTask:
    for task in TASKS:
        if task.NAME == name:
            return task(args)
    raise ValueError(f"Unknown task: {name}")
