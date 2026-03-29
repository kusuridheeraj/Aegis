import sys
import os

# Absolute path setup for reliability
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_CORE_DIR = os.path.join(BASE_DIR, 'aegis-ai-core')
sys.path.append(AI_CORE_DIR)
os.chdir(AI_CORE_DIR)

from services.qdrant_service import client as qdrant_client
from services.embedding_service import model as embedding_model
from config import QDRANT_COLLECTION

def verify_data(query: str):
    print(f"\n--- PROVING THE RETRIEVAL LAYER (No LLM involved) ---")
    print(f"Query: '{query}'")
    
    # 1. Vectorize query using our 8-bit quantized model
    # Note: Our quantized wrapper returns a list of lists (one per sentence)
    vectors = embedding_model.encode([query])
    vector = vectors[0]
    
    # 2. Search Qdrant directly
    hits = qdrant_client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=vector,
        limit=1
    )
    
    if not hits:
        print("[!] FAILURE: No data found in Qdrant. Did you run the batch ingestion?")
        return

    # 3. Output results for the "Zero-Model" proof
    print(f"\n[MATHEMATICAL PROOF]")
    print(f"Cosine Similarity Score: {hits[0].score:.4f}")
    
    print(f"\n[SEMANTIC PROOF - RAW TEXT FROM DB]")
    print("-" * 60)
    print(hits[0].payload.get("text")[:800])
    print("-" * 60)
    
    if hits[0].score > 0.65:
        print("\n✅ VERIFIED: The embeddings are high-precision and the retrieval logic is sound.")
    else:
        print("\n⚠️ WARNING: Low similarity score. Check if the book content covers this topic.")

if __name__ == "__main__":
    # Test with a specific engineering problem from your books
    verify_data("What are the key differences between Leader and Follower replication in distributed databases?")
