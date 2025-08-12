from google import genai
from google.genai import types
import os
from pathlib import Path
import subprocess
import sys


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

# Configure the client
client = genai.Client(api_key=api_key)


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


def add_target_to_build(target: str):
    """Adds a GN target / label to the Fuchsia build.

    Args:
        target: GN target to include.

    """
    print(f"ADD TARGET: {target}")
    with open("out/default/args.gn", "a") as f:
        f.write("\n# added by agent\n")
        f.write(f'developer_test_labels += ["{target}"]\n')


def read_file(path: str) -> str:
    """Read the contents of a file in the Fuchsia source tree.


    Args:
        path: the path to the file, relative to the root of the Fuchsia tree.


    Returns:
        the contents of the file if it exists.
    """
    print(f"READ FILE: {path}")
    return open(path, "r").read()


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


# Configure generation settings
config = types.GenerateContentConfig(
    tools=[
        # types.Tool(google_search=types.GoogleSearch()),
        # types.Tool(code_execution=types.ToolCodeExecution()),
        fx_build,
        add_target_to_build,
        read_file,
        write_file,
        list_directory,
    ]
)

PROMPT_PREAMBLE = """
You are an experienced operating system engineer working on the Fuchsia
operating system. You are confident in developing software in a wide variety
of programming languages with a wide variety of tools.

Fuchsia is primarily implemented in C++ and Rust. It primarilly uses the GN
build system (with Ninja), but some parts also use Bazel. Build errors from GN
and Ninja reference paths relative to the directory out/default.
"""

COMPONENT_DIR = "src/developer/build_info"
COMPONENT_TARGET = "//src/developer/build_info:build-info"

TASK_PROMPT = f"""
Migrate the component in the directory "{COMPONENT_DIR}" from the HLCPP FIDL bindings to the new C++ bindings.

Documentation covering the differences between the HLCPP and new C++ bindings are in: docs/development/languages/fidl/guides/c-family-comparison.md

You can build the component by building the target "{COMPONENT_TARGET}".

Once you have modified the files you must build the component and fix any compile errors that have been introduced.

Keep iterating on your changes until the component builds without any errors.

"""


prompt = PROMPT_PREAMBLE + TASK_PROMPT

while True:
    # Make the request
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )

    # Print the grounded response
    print(f"RESPONSE: {response.text}")

    # check if we're done.
    try:
        subprocess.check_call(["fx", "build", "-q", COMPONENT_TARGET])
    except:
        print("Let's try again...")
        continue

    print("all done")
    break

    # if response.text is None:
    #     from pprint import pprint

    #     pprint(response)
    #     from pdb import set_trace

    #     set_trace()


# pprint(response, depth=30)


# for i, part in enumerate(response.candidates[0].content.parts):
#     print(f"Part {i}:")
#     pprint(part)
#     if part.text is not None:
#         print(part.text)
#     if part.executable_code is not None:
#         print(part.executable_code.code)
#     if part.code_execution_result is not None:
#         print(part.code_execution_result.output)
