from google import genai
from google.genai import types
import os
from pathlib import Path
import subprocess
import sys

import tools


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

# Configure generation settings
config = types.GenerateContentConfig(tools=tools.TOOLS)

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
