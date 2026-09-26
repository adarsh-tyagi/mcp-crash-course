import json
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from tools import add


# Interactive cells have no __file__; open them from this lesson folder.
SCRIPT_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

load_dotenv(SCRIPT_DIR.parent / ".env")


"""
This is a simple example to demonstrate that MCP simply enables a new way to call functions.
"""

# Define tools for the model (Gemini uses LangChain tool schema)
tools = [
    {
        "name": "add",
        "description": "Add two numbers together",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "integer", "description": "First number"},
                "b": {"type": "integer", "description": "Second number"},
            },
            "required": ["a", "b"],
        },
    }
]

# Initialize Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",  # or another available model
    google_api_key=None,       # will read GOOGLE_API_KEY from env if None
)


# Bind tools to the model
llm_with_tools = llm.bind_tools(tools)


# Call LLM
messages = [HumanMessage(content="Calculate 25 + 17")]
response = llm_with_tools.invoke(messages)


# Handle tool calls
if hasattr(response, "tool_calls") and response.tool_calls:
    tool_call = response.tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]

    # Execute directly
    result = add(**tool_args)

    # Build messages for second turn
    messages_after_tool = [
        HumanMessage(content="Calculate 25 + 17"),
        AIMessage(
            content=response.content or "",
            tool_calls=[tool_call],
        ),
        ToolMessage(content=str(result), tool_call_id=tool_call["id"]),
    ]

    # Send result back to model
    final_response = llm_with_tools.invoke(messages_after_tool)
    print(final_response.content)
else:
    # No tool call; just print the response
    print(response.content)