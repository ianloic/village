import tools
import argparse

from .base_task import _BaseTask


class HlcppMigration(_BaseTask):
    """Migrate a C++ component from HLCPP to Natural bindings"""

    NAME = "hlcpp-migration"

    @staticmethod
    def register_arguments(parser: argparse.ArgumentParser):
        parser.add_argument(
            "--component-dir",
            type=str,
            required=True,
            help="The directory of the component to migrate.",
        )
        parser.add_argument(
            "--component-target",
            type=str,
            help="The GN target of the component to migrate.",
        )

    def __init__(self, args):
        self.component_dir = args.component_dir
        self.component_target = args.component_target or f"//{args.component_dir}"

    def preflight(self):
        assert tools.check_gn_label(self.component_target)

    @property
    def tools(self) -> list:
        # all of the tools
        return tools.TOOLS

    @property
    def prompt(self) -> str:
        return f"""
Migrate the component in the directory "{self.component_dir}" from the HLCPP
FIDL bindings to the new Natural C++ bindings.

Documentation covering the differences between the HLCPP and new C++ bindings
are in: docs/development/languages/fidl/guides/c-family-comparison.md

Documentation specifically about the new C++ bindings are in:
docs/reference/fidl/bindings/cpp-bindings.md

If the component already uses the wire or natural bindings in some places leave
that code alone and only modify the parts of the component that use HLCPP.

You can build the component by building the target "{self.component_target}".

Once you have modified the files you must build the component and fix any
compile errors that have been introduced.

Keep iterating on your changes until the component builds without any errors.

Never try to add realm builder support. The label
`//sdk/lib/component/testing/cpp` does not exist.

Before referencing new targets or labels in BUILD.gn files you MUST ALWAYS use
the {tools.check_gn_label.__name__} tool to validate that the label exists.

After migration from HLCPP to natural bindings is complete, remove lines
referencing {self.component_target} from "build/cpp/hlcpp_visibility.gni". Do
not modify any other lines.

"""


# # Configure generation settings

# COMPONENT_DIR = "src/developer/build_info"
# # COMPONENT_TARGET = f"//{COMPONENT_DIR}"
# COMPONENT_TARGET = f"//{COMPONENT_DIR}:build-info"
