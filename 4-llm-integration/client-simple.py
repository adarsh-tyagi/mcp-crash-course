import asyncio
import json
import sys
from pathlib import Path

import nest_asyncio
from dotenv import load_dotenv

from google import genai
from google.genai import types

from mcp import Client, StdioServerParameters


# ---------------------------------------------------------
# Jupyter / IPython support
# ---------------------------------------------------------

nest_asyncio.apply()


# ---------------------------------------------------------
# Project path
# ---------------------------------------------------------

SCRIPT_DIR = (
    Path(__file__).resolve().parent
    if "__file__" in globals()
    else Path.cwd()
)


# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

load_dotenv(SCRIPT_DIR.parent / ".env")


# ---------------------------------------------------------
# Google GenAI
# ---------------------------------------------------------

google_client = genai.Client()

MODEL = "gemini-2.5-flash-lite"


# ---------------------------------------------------------
# MCP server
# ---------------------------------------------------------

server_params = StdioServerParameters(
    command=sys.executable,
    args=[
        str(SCRIPT_DIR / "server.py")
    ],
)


# ---------------------------------------------------------
# Convert MCP tools -> Gemini tools
# ---------------------------------------------------------

def convert_mcp_tools_to_gemini(
    tools_result,
):
    """
    Convert MCP tool definitions into Gemini
    FunctionDeclaration objects.
    """

    function_declarations = []

    for tool in tools_result.tools:

        function_declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or "",
                parameters_json_schema=tool.input_schema,
            )
        )

    return types.Tool(
        function_declarations=function_declarations
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

async def main():

    async with Client(server_params) as mcp_client:

        print("Connected to MCP server")

        # -------------------------------------------------
        # Server information
        # -------------------------------------------------

        if mcp_client.server_info:
            print(
                f"Server: "
                f"{mcp_client.server_info.name}"
            )
            print(
                f"Version: "
                f"{mcp_client.server_info.version}"
            )

        print(
            f"Protocol version: "
            f"{mcp_client.protocol_version}"
        )

        # -------------------------------------------------
        # Get MCP tools
        # -------------------------------------------------

        tools_result = await mcp_client.list_tools()

        print("\nAvailable MCP tools:")

        for tool in tools_result.tools:
            print(f"\n- {tool.name}")
            print(
                f"  Description: "
                f"{tool.description}"
            )
            print(
                f"  Input Schema: "
                f"{tool.input_schema}"
            )

        # -------------------------------------------------
        # Convert MCP -> Gemini
        # -------------------------------------------------

        gemini_tools = convert_mcp_tools_to_gemini(
            tools_result
        )

        # -------------------------------------------------
        # Query
        # -------------------------------------------------

        query = (
            "What is our company's vacation policy?"
        )

        print(f"\nQuery: {query}")

        # -------------------------------------------------
        # First Gemini call
        # -------------------------------------------------

        response = await google_client.aio.models.generate_content(
            model=MODEL,
            contents=query,
            config=types.GenerateContentConfig(
                temperature=0,
                tools=[gemini_tools],
            ),
        )

        # -------------------------------------------------
        # Inspect Gemini response
        # -------------------------------------------------

        candidate = response.candidates[0]

        tool_calls = []

        for part in candidate.content.parts:
            if part.function_call:
                tool_calls.append(
                    part.function_call
                )

        # -------------------------------------------------
        # No tool call
        # -------------------------------------------------
        if not tool_calls:
            print("\nResponse:")
            print(response.text)
            return

        # -------------------------------------------------
        # Execute MCP tools
        # -------------------------------------------------

        function_responses = []

        for function_call in tool_calls:
            tool_name = function_call.name
            tool_args = (
                dict(function_call.args)
                if function_call.args
                else {}
            )
            print(
                f"\nCalling MCP tool: "
                f"{tool_name}"
            )
            print(
                f"Arguments: {tool_args}"
            )

            # ---------------------------------------------
            # MCP 2.x tool execution
            # ---------------------------------------------

            tool_result = await mcp_client.call_tool(
                tool_name,
                tool_args,
            )

            print(
                f"Tool result: "
                f"{tool_result}"
            )

            # ---------------------------------------------
            # Extract result for Gemini
            # ---------------------------------------------

            result_text = ""

            for content in tool_result.content:
                if hasattr(content, "text"):
                    result_text += content.text

            function_responses.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response={
                        "result": result_text
                    },
                )
            )

        # -------------------------------------------------
        # Send tool result back to Gemini
        # -------------------------------------------------

        final_response = (
            await google_client.aio.models.generate_content(
                model=MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(
                                text=query
                            )
                        ],
                    ),
                    candidate.content,
                    types.Content(
                        role="user",
                        parts=function_responses,
                    ),
                ],
                config=types.GenerateContentConfig(
                    temperature=0,
                    tools=[gemini_tools],
                ),
            )
        )

        # -------------------------------------------------
        # Final answer
        # -------------------------------------------------

        print("\nResponse:")
        print(final_response.text)


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())