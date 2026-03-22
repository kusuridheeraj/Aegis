import json
import logging
from kafka import KafkaConsumer
from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC
from services.minio_service import download_document
from services.embedding_service import extract_text_from_pdf, chunk_text, generate_embeddings
from services.qdrant_service import store_vectors

logger = logging.getLogger(__name__)

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
        
        if not object_id:
            logger.error("Received event without objectId, skipping.")
            continue

        logger.info(f"Received ingestion event for: {filename} ({object_id})")
        
        try:
            # 1. Claim Check Retrieval
            file_bytes = download_document(object_id)
            
            # 2. Extract Text (Supports PDFs and raw text)
            raw_text = extract_text_from_pdf(file_bytes)
            
            if not raw_text.strip():
                logger.warning(f"No extractable text found in {object_id}")
                continue

            # 3. Chunking
            chunks = chunk_text(raw_text)
            logger.info(f"Document split into {len(chunks)} chunks.")

            # 4. Vector Generation
            embeddings = generate_embeddings(chunks)

            # 5. Store in Qdrant
            store_vectors(object_id, chunks, embeddings)
            logger.info(f"Successfully processed and indexed {object_id}")

        except Exception as e:
            logger.error(f"Failed to process document {object_id}: {e}")
