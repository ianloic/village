"""
Tools that we offer to the assistant.
"""

import os
import subprocess
import sys
import typing

TOOLS = []

on_success: None | typing.Callable[[str], None] = None
on_failure: None | typing.Callable[[str], None] = None


class WrappedTool:
    """Wraps a function to be used as a tool."""

    def __init__(self, func):
        self.func = func
        self.name = func.__name__
        self.description = func.__doc__
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def tool(func):
    """A decorator that adds the decorated function to the global TOOLS list."""
    TOOLS.append(func)
    return WrappedTool(func)


def check_path(path: str):
    """Check that a path isn't weird"""
    assert ".." not in path
    assert not path.startswith("/")


def run_command_lines(command: list[str]) -> dict:
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

    process.wait()
    if process.returncode != 0:
        print(f"RETURNED: {process.returncode}")

    return {"success": process.returncode == 0, "output": captured_output}


def run_command(command: list[str]) -> dict:
    result = run_command_lines(command)
    return {"success": result["success"], "output": "".join(result["output"])}


@tool
def fx_build(target: str) -> dict:
    """Build the Fuchsia source tree.

    Args:
        target: GN target to build. If it's omitted the whole tree will be
        built.

    Returns:
        A dictionary with a "success" member indicating if the build succeeded
        and an "output" member holding the output from the build tools.
    """

    print(f"BUILD: {target}")
    command = [
        "fx",
        "build",
        "-q",
    ]
    if target:
        command.append(target)
    return run_command(command)


@tool
def fx_test(test_name: str) -> str:
    """Run a test. This isn't implemented yet."""

    return ""


@tool
def check_gn_label(label: str) -> bool:
    """Quickly checks if a GN label is probably valid.
    This is a heuristic check but helpful to avoid mistakes when updating BUILD.gn files.

    Args:
        label: GN label to check.

    Returns:
        True if the label is probably valid, False otherwise.
    """

    # TODO: see if calling `gn desc` works better

    print(f"CHECK GN LABEL: {label}")
    if not label.startswith("//"):
        return False
    path = label[2:]
    if "(" in path:
        # trim toolchain
        path = path.split("(", 1)[0]
    exists = run_command_lines(["ninja", "-C", "out/default", "-t", "query", path])[
        "success"
    ]
    print(f"CHECK GN LABEL {label}: {exists}")
    return exists


@tool
def read_file(path: str) -> str:
    """Read the contents of a file in the Fuchsia source tree.


    Args:
        path: the path to the file, relative to the root of the Fuchsia tree.


    Returns:
        the contents of the file if it exists.
    """
    print(f"READ FILE: {path}")

    check_path(path)

    return open(path, "r").read()


@tool
def read_files(paths: list[str]) -> dict[str, str]:
    """Read the contents of multiple files in the Fuchsia source tree.


    Args:
        paths: a list of paths to the files, relative to the root of the Fuchsia
        tree.


    Returns:
        a list dictionary whose keys are the file paths and whose values are
        contents of each file, if they exist.
    """
    print(f"READ FILES: {' '.join(paths)}")

    files = {}
    for path in paths:
        check_path(path)
        try:
            files[path] = open(path, "r").read()
        except Exception as e:
            print(f"READ FILE {path} failed: {e}")

    return files


@tool
def write_file(path: str, contents: str) -> None:
    """Overwrite the contents of a file in the Fuchsia source tree.


    Args:
        path: the path to the file, relative to the root of the Fuchsia tree.
        contents: the contents to write to the file.

    """
    print(f"WRITE FILE: {path} ({len(contents)} bytes)")

    check_path(path)

    diff = False
    orig = path + ".orig"
    if os.path.exists(path):
        assert not os.path.exists(orig)
        os.rename(path, orig)
        diff = True

    with open(path, "wt") as f:
        f.write(contents)

    if diff:
        subprocess.call(["diff", "-u", orig, path])
        os.unlink(orig)


@tool
def list_directory(path: str) -> list[str]:
    """List the contents of a directory in the Fuchsia source tree.


    Args:
        path: the path to the directory, relative to the root of the Fuchsia tree.

    Returns:
        a list of files and subdirectories. The subdirectories will end in a forward-slash (/).
    """
    print(f"LIST DIRECTORY: {path}")
    check_path(path)
    contents = []
    for entry in os.listdir(path):
        if os.path.isdir(os.path.join(path, entry)):
            contents.append(entry + "/")
        else:
            contents.append(entry)
    return contents


def git_grep(path: str, pattern: str, regex: bool) -> list[str]:
    check_path(path)
    command = ["git"]
    if path:
        command.extend(["-C", path])
    command.extend(["grep", "--files-with-matches"])
    if not regex:
        command.append("--fixed-strings")
    command.append(pattern)

    grep = run_command_lines(command)
    if grep["success"]:
        relative_paths = grep["output"]
        absolute_paths = []
        for relative_path in relative_paths:
            absolute_paths.append(os.path.join(path, relative_path.strip()))
        print(f"GIT GREP RETURNS: {repr(absolute_paths)}")
        return absolute_paths
    else:
        print("GIT GREP FAILED")
        return []


@tool
def search_directory(path: str, substring: str) -> list[str]:
    """Recursively for a substring in a directory in the Fuchsia source tree.
    This only searches files under source control, not those that are generated as part of the build.


    Args:
        path: the path of a directory, relative to the root of the Fuchsia tree. Empty if you want to search the whole tree.
        substring: the substring to search for.

    Returns:
        a list of files that contain the string. The paths are relative to the Fuchsia source root.
    """
    print(f"SEARCH DIRECTORY: {path} for {repr(substring)}")
    check_path(path)
    return git_grep(path, substring, False)


@tool
def regex_search_directory(path: str, pattern: str) -> list[str]:
    """Recursively for a regular expression in a directory in the Fuchsia source tree. Empty if you want to search the whole tree.
    This only searches files under source control, not those that are generated as part of the build.


    Args:
        path: the path of a directory, relative to the root of the Fuchsia tree.
        pattern: the regular expression to search for in basic POSIX regex syntax

    Returns:
        a list of files that contain the string. The paths are relative to the Fuchsia source root.
    """
    print(f"REGEX SEARCH DIRECTORY: {path} for {repr(pattern)}")
    check_path(path)
    return git_grep(path, pattern, True)


@tool
def success(message: str):
    """Report to the user that the task has been completed successfully.


    Args:
        message: a message to present to the user describing the work that has been done.
    """
    print(f"SUCCESS: {message}")
    if on_success is not None:
        on_success(message)
    else:
        sys.exit(0)


@tool
def fail(message: str):
    """Report to the user that the task has failed.

    Args:
     message: a message to present to the user describing why the task failed
     including information that was missing or invalid, things that were too
     confusing, etc.
    """
    print(f"FAIL: {message}")
    if on_failure is not None:
        on_failure(message)
    else:
        sys.exit(1)
