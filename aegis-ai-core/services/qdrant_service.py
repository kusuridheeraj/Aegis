import logging
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from config import QDRANT_URL, QDRANT_COLLECTION

logger = logging.getLogger(__name__)

# Initialize Qdrant Client using REST API
client = QdrantClient(url=QDRANT_URL)

def init_collection():
    """Ensures the Qdrant collection exists with the correct vector dimensions."""
    collections = client.get_collections().collections
    if not any(c.name == QDRANT_COLLECTION for c in collections):
        logger.info(f"Creating Qdrant collection '{QDRANT_COLLECTION}'...")
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

# Run initialization on startup
init_collection()

def store_vectors(object_id: str, chunks: list[str], embeddings: list[list[float]]):
    """Inserts the vectors and the original text (payload) into Qdrant."""
    if not chunks or not embeddings:
        return

    points = []
    for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        # Generate a deterministic UUID for this chunk
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{object_id}_{i}"))
        
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "object_id": object_id,
                    "chunk_index": i,
                    "text": chunk
                }
            )
        )
    
    logger.info(f"Upserting {len(points)} vectors into Qdrant for object: {object_id}")
    client.upsert(
        collection_name=QDRANT_COLLECTION,
        points=points
    )
