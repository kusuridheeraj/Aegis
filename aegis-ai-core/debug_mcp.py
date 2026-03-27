import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_handshake():
    print("--- Initiating MCP Handshake Test ---")
    
    # Define the parameters to start our server
    # We use the python executable from the venv to run our script
    server_params = StdioServerParameters(
        command="./venv/Scripts/python.exe",
        args=["mcp_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize
            print("Connecting to Aegis MCP Server...")
            await session.initialize()
            
            # 2. List tools
            print("Querying available tools...")
            tools = await session.list_tools()
            print(f"Found tools: {[t.name for t in tools.tools]}")

            # 3. Call the search tool
            print("\n--- Testing 'search_documents' tool call ---")
            query = "Jennifer Doudna discovery"
            print(f"Executing search for: '{query}'")
            
            result = await session.call_tool(
                "search_documents",
                arguments={"query": query}
            )
            
            print("\n[TOOL CALL SUCCESSFUL]")
            print("Result received from MCP Server:")
            print("-" * 50)
            print(result.content[0].text[:500] + "...")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_handshake())
