import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult
from services.qdrant_service import client as qdrant_client
from services.embedding_service import model
from config import QDRANT_COLLECTION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis-mcp")

# Initialize the MCP Server
app = Server("aegis-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Exposes the search capability to any connecting AI agent."""
    return [
        Tool(
            name="search_documents",
            description="Search the Aegis Enterprise RAG database for relevant document chunks based on a semantic query. Use this to answer questions about internal knowledge.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "The natural language search query."
                    }
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles the execution of the tools exposed by the server."""
    if name != "search_documents":
        raise ValueError(f"Unknown tool: {name}")
    
    query = arguments.get("query")
    if not query:
        raise ValueError("Query argument is required.")
        
    logger.info(f"Received semantic search query: {query}")
    
    # 1. Convert the text query into a mathematical vector
    query_vector = model.encode(query).tolist()
    
    # 2. Perform a high-speed cosine similarity search in Qdrant
    search_result = qdrant_client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_vector,
        limit=5 # Return the top 5 most relevant chunks
    )
    
    # 3. Format the results for the LLM
    if not search_result:
        return [TextContent(type="text", text="No relevant documents found in the database.")]
        
    formatted_results = []
    for hit in search_result:
        doc_name = hit.payload.get('object_id', 'Unknown Document')
        chunk_text = hit.payload.get('text', '')
        formatted_results.append(f"Source: {doc_name}\nContent: {chunk_text}")
        
    final_text = "\n\n---\n\n".join(formatted_results)
    
    return [TextContent(type="text", text=final_text)]

async def main():
    """Runs the MCP server over standard input/output."""
    logger.info("Starting Aegis MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
