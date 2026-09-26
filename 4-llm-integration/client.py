import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import nest_asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import Client, StdioServerParameters


# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()


# Interactive cells have no __file__
SCRIPT_DIR = (
    Path(__file__).resolve().parent
    if "__file__" in globals()
    else Path.cwd()
)


# Load environment variables
load_dotenv(SCRIPT_DIR.parent / ".env")


class MCPGenAIClient:
    """Client for interacting with Google Gemini models using MCP tools."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash-lite",
    ):
        """
        Initialize the Google GenAI MCP client.

        Args:
            model: Gemini model to use.
        """
        self.mcp_client: Optional[Client] = None
        self.google_client = genai.Client()
        self.model = model

    async def connect_to_server(
        self,
        server_script_path: str = "server.py",
    ):
        """
        Connect to an MCP server.

        Args:
            server_script_path: Path to the MCP server script.
        """

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[
                str(SCRIPT_DIR / server_script_path)
            ],
        )

        # MCP 2.x client
        self.mcp_client = Client(server_params)

        await self.mcp_client.__aenter__()

        print("\nConnected to MCP server")

        if self.mcp_client.server_info:
            print(
                f"Server: "
                f"{self.mcp_client.server_info.name} "
                f"{self.mcp_client.server_info.version}"
            )

        print(
            f"Protocol version: "
            f"{self.mcp_client.protocol_version}"
        )

        # List available tools
        tools_result = await self.mcp_client.list_tools()

        print("\nConnected to server with tools:")

        for tool in tools_result.tools:
            print(
                f"  - {tool.name}: "
                f"{tool.description}"
            )

    async def get_mcp_tools(
        self,
    ) -> List[types.FunctionDeclaration]:
        """
        Convert MCP tools into Gemini FunctionDeclaration objects.
        """

        if self.mcp_client is None:
            raise RuntimeError(
                "MCP client is not connected."
            )

        tools_result = await self.mcp_client.list_tools()

        gemini_functions = []

        for tool in tools_result.tools:

            gemini_function = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or "",
                parameters_json_schema=tool.input_schema,
            )

            gemini_functions.append(
                gemini_function
            )

        return gemini_functions

    async def process_query(
        self,
        query: str,
    ) -> str:
        """
        Process a query using Gemini and available MCP tools.
        """

        if self.mcp_client is None:
            raise RuntimeError(
                "MCP client is not connected."
            )

        # --------------------------------------------------
        # Get MCP tools
        # --------------------------------------------------

        gemini_functions = await self.get_mcp_tools()

        # Create Gemini Tool
        gemini_tool = types.Tool(
            function_declarations=gemini_functions
        )

        # --------------------------------------------------
        # Initial Gemini API call
        # --------------------------------------------------

        response = await self.google_client.aio.models.generate_content(
            model=self.model,
            contents=query,
            config=types.GenerateContentConfig(
                temperature=0,
                tools=[gemini_tool],
            ),
        )

        # --------------------------------------------------
        # Check if Gemini requested a tool
        # --------------------------------------------------

        if not response.function_calls:
            return response.text

        # --------------------------------------------------
        # Store conversation contents
        # --------------------------------------------------

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=query
                    )
                ],
            ),
            response.candidates[0].content,
        ]

        # --------------------------------------------------
        # Execute Gemini requested functions
        # --------------------------------------------------

        for function_call in response.function_calls:
            tool_name = function_call.name
            tool_args = (
                dict(function_call.args)
                if function_call.args
                else {}
            )
            print(
                f"\nCalling MCP tool: {tool_name}"
            )
            print(
                f"Arguments: {tool_args}"
            )

            # Execute MCP tool
            result = await self.mcp_client.call_tool(
                tool_name,
                tool_args,
            )

            # --------------------------------------------------
            # Extract MCP result
            # --------------------------------------------------

            result_text = ""

            for content in result.content:
                if hasattr(content, "text"):
                    result_text += content.text
                else:
                    result_text += str(content)

            print(
                f"Tool result: {result_text}"
            )

            # --------------------------------------------------
            # Convert MCP result -> Gemini function response
            # --------------------------------------------------

            function_response_part = (
                types.Part.from_function_response(
                    name=tool_name,
                    response={
                        "result": result_text
                    },
                )
            )

            contents.append(
                types.Content(
                    role="tool",
                    parts=[
                        function_response_part
                    ],
                )
            )

        # --------------------------------------------------
        # Send tool results back to Gemini
        # --------------------------------------------------

        final_response = (
            await self.google_client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0,
                    tools=[gemini_tool],
                ),
            )
        )

        return final_response.text

    async def cleanup(self):
        """Clean up MCP and Google GenAI resources."""

        try:

            if self.mcp_client is not None:
                await self.mcp_client.__aexit__(
                    None,
                    None,
                    None,
                )

        finally:

            await self.google_client.aio.aclose()


async def main():
    """Main entry point."""

    client = MCPGenAIClient()
    try:
        await client.connect_to_server(
            "server.py"
        )

        # Example query
        query = (
            "What is our company's vacation policy?"
        )
        print(
            f"\nQuery: {query}"
        )

        response = await client.process_query(
            query
        )
        print(
            f"\nResponse: {response}"
        )

    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())