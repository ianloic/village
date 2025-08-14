from google import genai
from google.genai import types
import os
from pathlib import Path
import subprocess

import system_prompt
import tools

MODEL = "gemini-2.5-flash"
# MODEL = "gemini-2.5-pro"


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
config = types.GenerateContentConfig(
    tools=tools.TOOLS, system_instruction=system_prompt.SYSTEM_PROMPT
)

COMPONENT_DIR = "src/devices/securemem/drivers/aml-securemem"
COMPONENT_TARGET = f"//{COMPONENT_DIR}"
assert tools.check_gn_label(COMPONENT_TARGET)


TASK_PROMPT = f"""
Migrate the component in the directory "{COMPONENT_DIR}" from the HLCPP FIDL
bindings to the new Natural C++ bindings.

Documentation covering the differences between the HLCPP and new C++ bindings
are in: docs/development/languages/fidl/guides/c-family-comparison.md

Documentation specifically about the new C++ bindings are in:
docs/reference/fidl/bindings/cpp-bindings.md

If the component already uses the wire or natural bindings in some places leave
that code alone and only modify the parts of the component that use HLCPP.

You can build the component by building the target "{COMPONENT_TARGET}".

Once you have modified the files you must build the component and fix any
compile errors that have been introduced.

Keep iterating on your changes until the component builds without any errors.

Never try to add realm builder support. The label
`//sdk/lib/component/testing/cpp` does not exist.

Before referencing new targets or labels in BUILD.gn files you MUST ALWAYS
{tools.read_file.__name__} tool to validate that the label exists.

After migration from HLCPP to natural bindings is complete, remove lines
referencing {COMPONENT_TARGET} from "build/cpp/hlcpp_visibility.gni". Do not
modify any other lines.

"""


chat = client.chats.create(model=MODEL, config=config)
prompt = TASK_PROMPT
while True:
    response = chat.send_message(prompt)
    if response.text is None:
        prompt = ""
    else:
        print(f"RESPONSE: {response.text}")
        prompt = input("USER: ")
