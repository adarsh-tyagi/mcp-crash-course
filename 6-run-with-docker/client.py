import asyncio
import nest_asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

nest_asyncio.apply()

"""
Make sure:
1. The server is running begore running this script
2. The server is configured to use SSE transport
3. The server is listening in port 8050

To run the server:
uv run server.py
"""


async def main():
    async with sse_client("http://localhost:8050/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            tools_result = await session.list_tools()
            print("Available tools")
            for tool in tools_result.tools:
                print(f"  - {tool.name} : {tool.description}")
                
            result = await session.call_tool("add", arguments={"a": 2, "b": 5})
            print(f"2+5 = {result.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())