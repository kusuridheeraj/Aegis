import json
import logging
import time
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, KAFKA_DLQ_TOPIC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis-dlq-replayer")

def replay_dlq():
    """
    Consumes events from the Dead Letter Queue (DLQ) and re-publishes them 
    to the main raw documents topic for re-processing.
    
    This is used after a system-wide failure (e.g. Qdrant or Kafka disk full) 
    has been resolved to ensure zero data loss.
    """
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
    
    # Initialize the Producer to push back to the main topic
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    # Initialize the Consumer to read from the DLQ
    consumer = KafkaConsumer(
        KAFKA_DLQ_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='aegis-dlq-replayer-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    # Check if there are messages to replay
    # Note: KafkaConsumer.poll() is needed to initialize the assignment
    logger.info(f"Scanning topic: {KAFKA_DLQ_TOPIC}...")
    
    # Get current offsets and end offsets to see if there's a backlog
    partitions = consumer.partitions_for_topic(KAFKA_DLQ_TOPIC)
    if not partitions:
        logger.warning(f"Topic {KAFKA_DLQ_TOPIC} does not exist or has no partitions.")
        return

    # We want to stop after we've read what's currently there
    topic_partitions = [TopicPartition(KAFKA_DLQ_TOPIC, p) for p in partitions]
    end_offsets = consumer.end_offsets(topic_partitions)
    
    total_replayed = 0
    start_time = time.time()
    
    logger.info("Starting DLQ Replay...")
    
    # Consume with a timeout so we don't wait forever on an empty topic
    messages = consumer.poll(timeout_ms=5000)
    
    if not messages:
        logger.info("No messages found in DLQ to replay.")
        return

    for tp, msgs in messages.items():
        for msg in msgs:
            dlq_payload = msg.value
            correlation_id = dlq_payload.get('correlationId', 'UNKNOWN')
            original_event = dlq_payload.get('originalEvent')
            error = dlq_payload.get('error', 'No error logged')
            
            if original_event:
                logger.info(f"[{correlation_id}] Replaying event for {original_event.get('originalFilename')}. Original Error: {error}")
                
                # Push back to the main topic
                producer.send(KAFKA_TOPIC, original_event)
                total_replayed += 1
            else:
                logger.error(f"[{correlation_id}] Malformed DLQ event (no originalEvent): {dlq_payload}")

    producer.flush()
    elapsed = time.time() - start_time
    logger.info(f"DLQ Replay Complete. Successfully replayed {total_replayed} messages in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    replay_dlq()
