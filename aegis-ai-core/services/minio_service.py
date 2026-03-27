import io
import logging
from minio import Minio
from minio.error import S3Error
from config import MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET

logger = logging.getLogger(__name__)

# Initialize MinIO Client
minio_client = Minio(
    MINIO_URL,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def download_document(object_id: str) -> bytes:
    """
    Downloads a document from MinIO into memory.
    For massive files, you would stream this to disk, but for PDFs/Text, 
    memory is usually fine for the AI worker.
    """
    try:
        logger.info(f"Downloading {object_id} from MinIO...")
        response = minio_client.get_object(MINIO_BUCKET, object_id)
        data = response.read()
        return data
    except S3Error as e:
        logger.error(f"MinIO error occurred during download: {e}")
        raise
    finally:
        response.close()
        response.release_conn()

def delete_document(object_id: str):
    """
    Garbage Collection: Removes the raw binary file from MinIO to save storage
    space once the semantic vectors have been safely stored in Qdrant.
    """
    try:
        minio_client.remove_object(MINIO_BUCKET, object_id)
    except S3Error as e:
        logger.error(f"Failed to delete {object_id} from MinIO: {e}")
        raise

def check_health() -> bool:
    """Verifies that the MinIO service is reachable and the bucket exists."""
    try:
        # Check if bucket exists
        if minio_client.bucket_exists(MINIO_BUCKET):
            return True
        logger.error(f"MinIO bucket '{MINIO_BUCKET}' does not exist.")
        return False
    except Exception as e:
        logger.error(f"MinIO Health Check Failed: {e}")
        return False
