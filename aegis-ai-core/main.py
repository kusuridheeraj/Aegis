import logging
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from kafka_consumer import start_consuming

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run Kafka Consumer in a background thread
    logger.info("Starting up Aegis AI Core...")
    loop = asyncio.get_event_loop()
    consumer_task = loop.run_in_executor(None, start_consuming)
    yield
    # Shutdown logic would go here
    logger.info("Shutting down Aegis AI Core...")

app = FastAPI(
    title="Aegis AI Core",
    description="Vector Embedding & Model Context Protocol (MCP) Server for Aegis",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Simple health check endpoint to verify the API is running."""
    return {"status": "ok", "service": "aegis-ai-core"}

if __name__ == "__main__":
    import uvicorn
    # Run the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)