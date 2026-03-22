import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "aegis.documents.raw")

MINIO_URL = os.getenv("MINIO_URL", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "aegis_admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "aegis_password")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "aegis-raw-docs")

QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "aegis_documents")
