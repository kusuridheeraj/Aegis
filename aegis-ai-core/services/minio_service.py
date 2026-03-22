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
        logger.error(f"MinIO error occurred: {e}")
        raise
    finally:
        response.close()
        response.release_conn()
