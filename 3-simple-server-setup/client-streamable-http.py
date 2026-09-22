import asyncio
from mcp import Client


async def main():
    # Connect to the MCP server using Streamable HTTP
    async with Client("http://localhost:8050/mcp") as client:

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