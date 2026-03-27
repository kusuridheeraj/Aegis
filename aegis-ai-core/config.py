import os
from dotenv import load_dotenv

# Load .env file from the current directory
load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "aegis.documents.raw")
KAFKA_DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", "aegis.documents.failed")

MINIO_URL = os.getenv("MINIO_URL", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "aegis_admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "aegis_password")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "aegis-raw-docs")

QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "aegis_documents")

# AI API Keys for Autonomous Agent
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
