import argparse
import typing

import tools


class _BaseTask:
    NAME = "FIXME"

    @staticmethod
    def register_arguments(parser: argparse.ArgumentParser):
        raise NotImplementedError(
            "register_arguments must be implemented by subclasses"
        )

    def __init__(self, args: argparse.Namespace):
        raise NotImplementedError("__init__ must be implemented by subclasses")

    def preflight(self):
        pass

    @property
    def tools(self) -> list[typing.Callable]:
        return tools.TOOLS

    @property
    def prompt(self) -> str:
        raise NotImplementedError("prompt must be implemented by subclasses")
