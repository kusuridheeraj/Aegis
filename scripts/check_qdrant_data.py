import logging
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="aegis-ai-core/.env")

QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "aegis_documents")

client = QdrantClient(url=QDRANT_URL)

def check_qdrant():
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    try:
        collections = client.get_collections().collections
        print(f"Available Collections: {[c.name for c in collections]}")
        
        if QDRANT_COLLECTION not in [c.name for c in collections]:
            print(f"ERROR: Collection '{QDRANT_COLLECTION}' does not exist.")
            return

        count = client.count(collection_name=QDRANT_COLLECTION)
        print(f"Total Vectors in '{QDRANT_COLLECTION}': {count.count}")
        
        if count.count > 0:
            print("\n--- SAMPLE PAYLOADS ---")
            results = client.scroll(collection_name=QDRANT_COLLECTION, limit=3)
            for record in results[0]:
                print(f"ID: {record.id}")
                print(f"Payload: {record.payload}")
                print("-" * 20)
        else:
            print("\nNo data found in the collection. Have you uploaded any documents yet?")
            
    except Exception as e:
        print(f"Error connecting to Qdrant: {e}")

if __name__ == "__main__":
    check_qdrant()
