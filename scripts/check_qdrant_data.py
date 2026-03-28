import sys
import os

# Get absolute paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_CORE_DIR = os.path.join(BASE_DIR, 'aegis-ai-core')

# Add to path
sys.path.append(AI_CORE_DIR)
os.chdir(AI_CORE_DIR)

from services.qdrant_service import client as qdrant_client
from config import QDRANT_COLLECTION

def check_data():
    print(f"--- Checking Qdrant Collection: {QDRANT_COLLECTION} ---")
    results, _ = qdrant_client.scroll(
        collection_name=QDRANT_COLLECTION,
        limit=5,
        with_payload=True,
        with_vectors=False
    )
    
    if not results:
        print("Collection is EMPTY.")
        return
        
    print(f"Found {len(results)} sample records:")
    for res in results:
        print(f"\nID: {res.id}")
        print(f"File: {res.payload.get('object_id')}")
        print(f"Text Snippet: {res.payload.get('text')[:300]}...")

if __name__ == "__main__":
    check_data()
