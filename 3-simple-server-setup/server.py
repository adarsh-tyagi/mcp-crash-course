from mcp.server.mcpserver import MCPServer
import sys


# Create an MCP server
mcp = MCPServer(
    name="Calculator",
)


# Add a simple calculator tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


# Run the server
if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport == "stdio":
        print("Running server with stdio transport", file=sys.stderr)
        mcp.run(transport="stdio")

    elif transport == "sse":
        print("Running server with SSE transport", file=sys.stderr)
        mcp.run(
            transport="sse",
            host="127.0.0.1",
            port=8050,
        )

    elif transport == "streamable-http":
        print("Running server with streamable HTTP transport", file=sys.stderr)
        mcp.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=8050,
            stateless_http=True,
        )

    else:
        raise ValueError(f"Unknown transport: {transport}")