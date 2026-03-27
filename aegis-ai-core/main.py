import logging
import asyncio
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from kafka_consumer import start_consuming
from kafka import KafkaConsumer
from dlq_replayer import replay_dlq
from services import minio_service, qdrant_service
from services.logging_service import setup_logger
from config import KAFKA_BOOTSTRAP_SERVERS

# Configure logging using the new centralized service
logger = setup_logger("aegis-ai", "aegis-ai")

def check_kafka_health():
    """Lightweight check to see if Kafka brokers are reachable."""
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            request_timeout_ms=2000,
            connections_max_idle_ms=5000
        )
        return len(consumer.topics()) > 0
    except Exception as e:
        logger.error(f"Kafka Health Check Failed: {e}")
        return False

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
    """
    Deep health check endpoint to verify all system dependencies.
    Used by Docker Compose and Orchestrators to determine service readiness.
    """
    kafka_ok = check_kafka_health()
    minio_ok = minio_service.check_health()
    qdrant_ok = qdrant_service.check_health()
    
    status = "ok" if (kafka_ok and minio_ok and qdrant_ok) else "degraded"
    
    return {
        "status": status,
        "service": "aegis-ai-core",
        "dependencies": {
            "kafka": "healthy" if kafka_ok else "unreachable",
            "minio": "healthy" if minio_ok else "unreachable",
            "qdrant": "healthy" if qdrant_ok else "unreachable"
        }
    }

@app.post("/api/v1/system/replay-dlq")
async def trigger_dlq_replay(background_tasks: BackgroundTasks):
    """
    Triggers the DLQ replayer in the background. 
    Moves failed events back to the main topic for reprocessing.
    """
    logger.info("Manual DLQ Replay triggered via API.")
    background_tasks.add_task(replay_dlq)
    return {"status": "accepted", "message": "DLQ Replay task started in background."}

if __name__ == "__main__":
    import uvicorn
    # Run the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)