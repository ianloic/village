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


def check_path(path: str):
    """Check that a path isn't weird"""
    assert ".." not in path
    assert not path.startswith("/")


def run_command_lines(command: list[str]) -> list[str]:
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

    return captured_output


def run_command(command: list[str]) -> str:
    return "".join(run_command_lines(command))


@tool
def fx_build(target: str) -> str:
    """Build the Fuchsia source tree.

    Args:
        target: GN target to build. If it's omitted the whole tree will be built.

    Returns:
        The build output.
    """

    print(f"BUILD: {target}")
    command = [
        "fx",
        "build",
        "-q",
    ]  # "--", "-k0"]
    if target:
        command.append(target)
    return run_command(command)


@tool
def fx_test(test_name: str) -> str:
    """Run a test. This isn't implemented yet."""

    return ""


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
def check_gn_label(label: str) -> bool:
    """Quickly checks if a GN label is probably valid.
    This is a heuristic check but helpful to avoid mistakes when updating BUILD.gn files.

    Args:
        label: GN label to check.

    Returns:
        True if the label is probably valid, False otherwise.
    """

    # TODO: try using `ninja -t query <label-without-leading-double-slash>`

    print(f"CHECK GN LABEL: {label}")
    if not label.startswith("//"):
        return False
    path = label[2:]
    if "(" in path:
        # trim toolchain
        path = path.split("(", 1)[0]
    exists = (
        subprocess.check_call(["ninja", "-t", "query", path], cwd="out/default") == 0
    )
    # if path.endswith("_cpp_natural") or path.endswith("_cpp_wire"):
    #     return False
    # if ":" in path:
    #     # trim target name from label, leaving directory.
    #     path = path.split(":", 1)[0]
    # exists = os.path.exists(path) and os.path.isdir(path)
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
    relative_paths = run_command_lines(command)
    absolute_paths = []
    for relative_path in relative_paths:
        absolute_paths.append(os.path.join(path, relative_path.strip()))
    print(f"GIT GREP RETURNS: {repr(absolute_paths)}")
    return absolute_paths


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
