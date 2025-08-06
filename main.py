# This script demonstrates how to build a simple agent that can use tools
# with the raw Gemini API, specifically leveraging function calling.
#
# To run this script, you will need the `google-generativeai` library.
# Install it with: `pip install -q -U google-generativeai`
#
# You will also need a Gemini API key. Get one from Google AI Studio and
# set it as an environment variable named `GEMINI_API_KEY`.
# Example: export GEMINI_API_KEY="your-api-key-here"

import os
import json
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool, FunctionResponse, ToolConfig

# --- Step 1: Configure the API Key ---
# The client automatically picks up the API key from the environment variable.
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"Failed to configure API key: {e}")
    exit()

# --- Step 2: Define the "Tool" (a Python function) and its Declaration ---
# This is the actual function the agent will call.
def get_current_weather(location: str, unit: str = "fahrenheit"):
    """
    Get the current weather in a given location. This is a mock function.
    In a real application, this would call a real weather API.
    """
    print(f"\n--- Calling tool: get_current_weather({location}, {unit}) ---")
    
    # Mock data for demonstration
    if "san francisco" in location.lower():
        if unit.lower() == "celsius":
            return {"temperature": 18, "unit": "celsius", "description": "Partly cloudy"}
        else:
            return {"temperature": 65, "unit": "fahrenheit", "description": "Partly cloudy"}
    elif "new york" in location.lower():
        if unit.lower() == "celsius":
            return {"temperature": 25, "unit": "celsius", "description": "Sunny"}
        else:
            return {"temperature": 77, "unit": "fahrenheit", "description": "Sunny"}
    
    return {"temperature": "N/A", "unit": unit, "description": "Weather data not found"}

# This is the "function declaration" that the model reads.
# It's a structured description of the tool.
get_current_weather_declaration = FunctionDeclaration(
    name="get_current_weather",
    description="Get the current weather in a given location",
    parameters={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA"
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "The temperature unit to use. Default is fahrenheit."
            }
        },
        "required": ["location"]
    }
)

# --- Step 3: Create the Generative Model with the Tool ---
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    tools=[get_current_weather_declaration],
    tool_config=ToolConfig(
        function_calling=ToolConfig.FunctionCallingConfig(
            mode=ToolConfig.FunctionCallingConfig.Mode.AUTO
        )
    )
)

# --- Step 4: The Chat Loop ---
# This loop handles the multi-turn conversation.
chat_history = []

def run_chat_session(prompt: str):
    """
    Sends a prompt to the model and processes the response, including tool calls.
    """
    global chat_history
    
    chat_history.append({"role": "user", "parts": [{"text": prompt}]})
    print(f"\nUser: {prompt}")

    # Send the prompt to the model with the tool definitions.
    response = model.generate_content(
        contents=chat_history
    )

    # Check for a function call in the model's response.
    try:
        call = response.candidates[0].content.parts[0].function_call
        
        # If the model wants to call a function, execute it.
        if call.name == "get_current_weather":
            print(f"AI suggests calling the tool '{call.name}' with arguments: {call.args}")
            
            # Execute the function with the arguments provided by the model.
            tool_output = get_current_weather(**call.args)
            
            # Add the model's request and the tool's output to the chat history.
            chat_history.append(response.candidates[0].content)
            chat_history.append(
                FunctionResponse(name=call.name, response={"content": tool_output})
            )
            
            print(f"Tool output: {tool_output}")
            
            # Send the tool output back to the model for a final response.
            final_response = model.generate_content(
                contents=chat_history
            )
            
            final_response_text = final_response.text
            print(f"\nAI: {final_response_text}")
            
    except AttributeError:
        # If there's no function call, just print the model's text response.
        final_response_text = response.text
        print(f"\nAI: {final_response_text}")
    
    # Append the model's final text response to the history.
    chat_history.append({"role": "model", "parts": [{"text": final_response_text}]})


if __name__ == "__main__":
    print("Agent is ready. Type your query or 'exit' to quit.")
    while True:
        user_input = input("\nEnter your query: ")
        if user_input.lower() == 'exit':
            break
        
        run_chat_session(user_input)
        
    print("\nGoodbye!")

