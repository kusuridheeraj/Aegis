import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Get absolute path of this script's directory
current_dir = Path(__file__).parent.absolute()

# Load environment variables with absolute path
load_dotenv(dotenv_path=current_dir / ".env")

# Configure logging using the centralized service
from services.logging_service import setup_logger
logger = setup_logger("aegis-mcp", "aegis-mcp")
logger.info(f"--- Aegis MCP Server starting up from {current_dir} ---")

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult
from services.qdrant_service import client as qdrant_client
from services.embedding_service import model
from services import qdrant_service, minio_service
from config import QDRANT_COLLECTION

# Initialize the MCP Server
app = Server("aegis-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Exposes the search and health capabilities to any connecting AI agent."""
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
        ),
        Tool(
            name="check_aegis_health",
            description="Checks the operational health of the Aegis infrastructure (MinIO, Qdrant, etc.). Use this if searches are failing.",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handles the execution of the tools exposed by the server."""
    if name == "search_documents":
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
            limit=5 
        )
        
        if not search_result:
            return [TextContent(type="text", text="No relevant documents found.")]
            
        formatted_results = []
        for hit in search_result:
            # Extract text and metadata safely
            payload = hit.payload or {}
            chunk_text = payload.get('text', '[No text content available]')
            source = payload.get('object_id', 'Unknown Source')
            score = hit.score
            
            formatted_results.append(f"Source: {source}\nRelevance Score: {score:.4f}\nContent: {chunk_text}")
            
        return [TextContent(type="text", text="\n\n---\n\n".join(formatted_results))]

    elif name == "check_aegis_health":
        minio_ok = minio_service.check_health()
        qdrant_ok = qdrant_service.check_health()
        
        status_msg = f"Aegis Infrastructure Status:\n- MinIO: {'ONLINE' if minio_ok else 'OFFLINE'}\n- Qdrant: {'ONLINE' if qdrant_ok else 'OFFLINE'}"
        return [TextContent(type="text", text=status_msg)]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Runs the MCP server over standard input/output."""
    logger.info("Starting Aegis MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
