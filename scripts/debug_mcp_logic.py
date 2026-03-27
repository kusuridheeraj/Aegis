import sys
import os

# Get absolute paths to avoid confusion
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_CORE_DIR = os.path.join(BASE_DIR, 'aegis-ai-core')

# Add to path
sys.path.append(AI_CORE_DIR)

# Change working directory so config.py loads correctly
os.chdir(AI_CORE_DIR)

from services.qdrant_service import client as qdrant_client
from services.embedding_service import model
from config import QDRANT_COLLECTION

def test_search(query: str):
    print(f"--- Simulating MCP Tool Call for Query: '{query}' ---")
    
    # 1. Vectorize
    vector = model.encode(query).tolist()
    
    # 2. Search
    results = qdrant_client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=vector,
        limit=2
    )
    
    # 3. Print
    if not results:
        print("No matches found.")
        return
        
    for i, res in enumerate(results):
        print(f"\n[Result {i+1}] (Score: {res.score:.4f})")
        print(f"Source: {res.payload.get('object_id')}")
        print(f"Text Snippet: {res.payload.get('text')[:300]}...")

if __name__ == "__main__":
    test_search("Jennifer Doudna CRISPR discovery")