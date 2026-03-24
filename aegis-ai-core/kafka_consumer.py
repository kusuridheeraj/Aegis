import json
import logging
import traceback
from kafka import KafkaConsumer, KafkaProducer
from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, KAFKA_DLQ_TOPIC
from services.minio_service import download_document
from services.embedding_service import extract_text, chunk_text, generate_embeddings
from services.qdrant_service import store_vectors

logger = logging.getLogger(__name__)

# Initialize DLQ Producer
dlq_producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_to_dlq(correlation_id: str, original_event: dict, error_msg: str):
    """Pushes failed events to the Dead Letter Queue for later retry/analysis."""
    dlq_payload = {
        "correlationId": correlation_id,
        "originalEvent": original_event,
        "error": error_msg
    }
    dlq_producer.send(KAFKA_DLQ_TOPIC, dlq_payload)
    dlq_producer.flush()
    logger.warning(f"[{correlation_id}] Event routed to DLQ topic: {KAFKA_DLQ_TOPIC}")

def start_consuming():
    """Background task to constantly listen to the Kafka topic."""
    logger.info(f"Starting Kafka Consumer on {KAFKA_BOOTSTRAP_SERVERS}, topic: {KAFKA_TOPIC}")
    
    # We use kafka-python-ng which doesn't require C++ build tools
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='aegis-ai-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    for message in consumer:
        event = message.value
        object_id = event.get('objectId')
        filename = event.get('originalFilename', 'unknown')
        correlation_id = event.get('correlationId', 'NO_CORRELATION_ID')
        
        if not object_id:
            logger.error(f"[{correlation_id}] Received event without objectId, skipping.")
            continue

        logger.info(f"[{correlation_id}] Received ingestion event for: {filename} ({object_id})")
        
        try:
            # 1. Claim Check Retrieval
            file_bytes = download_document(object_id)
            logger.info(f"[{correlation_id}] Successfully downloaded payload from MinIO.")
            
            # 2. Extract Text (Intelligently handles PDFs, logs, code, markdown)
            raw_text = extract_text(file_bytes, filename)
            
            if not raw_text.strip():
                logger.warning(f"[{correlation_id}] No extractable text found in {object_id}")
                continue

            # 3. Chunking
            chunks = chunk_text(raw_text)
            logger.info(f"[{correlation_id}] Document split into {len(chunks)} chunks.")

            # 4. Vector Generation
            embeddings = generate_embeddings(chunks)
            logger.info(f"[{correlation_id}] Generated {len(embeddings)} vectors.")

            # 5. Store in Qdrant
            store_vectors(object_id, chunks, embeddings, correlation_id)
            logger.info(f"[{correlation_id}] Successfully processed and indexed {object_id}")

        except Exception as e:
            error_details = str(e)
            logger.error(f"[{correlation_id}] Failed to process document {object_id}: {error_details}")
            send_to_dlq(correlation_id, event, error_details)
