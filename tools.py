"""
Tools that we offer to the assistant.
"""

import os
import subprocess
import sys

TOOLS = []


def tool(func):
    """A decorator that adds the decorated function to the global TOOLS list."""
    TOOLS.append(func)
    return func


def run_command(command: list[str]) -> str:
    print(f"RUN: {' '.join(command)}")

    # fewer stats
    env = dict(os.environ)
    del env["FX_BUILD_RBE_STATS"]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    captured_output = []
    if process.stdout:
        for line in iter(process.stdout.readline, ""):
            # Print to the console in real-time
            sys.stdout.write("OUTPUT: " + line)
            # Store for the final returned string
            captured_output.append(line)

    # process.wait()
    # return_code = process.returncode
    # print(f"--- Command finished with exit code: {return_code} ---")

    return "".join(captured_output)


@tool
def fx_build(target: str) -> str:
    """Build the Fuchsia source tree.

    Args:
        target: GN target to build. If it's omitted the whole tree will be built.

    Returns:
        The build output.
    """

    command = ["fx", "build", "-q"]
    if target:
        command.append(target)
    return run_command(command)


@tool
def add_target_to_build(target: str):
    """Adds a GN target / label to the Fuchsia build.

    Args:
        target: GN target to include.

    """
    print(f"ADD TARGET: {target}")
    with open("out/default/args.gn", "a") as f:
        f.write("\n# added by agent\n")
        f.write(f'developer_test_labels += ["{target}"]\n')


@tool
def read_file(path: str) -> str:
    """Read the contents of a file in the Fuchsia source tree.


    Args:
        path: the path to the file, relative to the root of the Fuchsia tree.


    Returns:
        the contents of the file if it exists.
    """
    print(f"READ FILE: {path}")
    return open(path, "r").read()


@tool
def write_file(path: str, contents: str) -> None:
    """Overwrite the contents of a file in the Fuchsia source tree.


    Args:
        path: the path to the file, relative to the root of the Fuchsia tree.
        contents: the contents to write to the file.

    """
    print(f"WRITE FILE: {path} ({len(contents)} bytes)")

    assert ".." not in path

    diff = False
    if os.path.exists(path):
        os.rename(path, path + ".orig")
        diff = True

    with open(path, "wt") as f:
        f.write(contents)

    if diff:
        subprocess.call(["diff", "-u", path + ".orig", path])


@tool
def list_directory(path: str) -> list[str]:
    """List the contents of a directory in the Fuchsia source tree.


    Args:
        path: the path to the directory, relative to the root of the Fuchsia tree.

    Returns:
        a list of files and subdirectories. The subdirectories will end in a forward-slash (/).
    """
    print(f"LIST DIRECTORY: {path}")
    contents = []
    for entry in os.listdir(path):
        if os.path.isdir(os.path.join(path, entry)):
            contents.append(entry + "/")
        else:
            contents.append(entry)
    return contents
