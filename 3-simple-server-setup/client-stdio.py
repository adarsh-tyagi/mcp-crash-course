import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


# Get the folder containing this client script
SCRIPT_DIR = (
    Path(__file__).resolve().parent
    if "__file__" in globals()
    else Path.cwd()
)


async def main():
    # Define the MCP server process
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SCRIPT_DIR / "server.py")],
    )

    # Connect to the server
    async with Client(server_params) as client:

        # List available tools
        tools_result = await client.list_tools()

        print("Available tools")
        for tool in tools_result.tools:
            print(f" - {tool.name}: {tool.description}")

        # Call calculator tool
        result = await client.call_tool(
            "add",
            {"a": 2, "b": 3},
        )

        print(f"2 + 3 = {result.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())