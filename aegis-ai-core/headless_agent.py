import os
import requests
import json
from services.embedding_service import model as embedding_model
from services.qdrant_service import client as qdrant_client
from config import QDRANT_COLLECTION, ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL

"""
Aegis Headless Agent (Manual RAG Loop)

This script simulates an autonomous agent without needing native MCP tool support.
It uses a 3-step loop:
1. Identify the search query.
2. Search Qdrant locally.
3. Summarize with the LLM.
"""

def search_qdrant(query: str):
    print(f"[*] Local Search: Executing Qdrant query for '{query}'...")
    vector = embedding_model.encode(query).tolist()
    results = qdrant_client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=vector,
        limit=3
    )
    context = ""
    for res in results:
        context += f"\n---\nSource: {res.payload.get('object_id')}\nContent: {res.payload.get('text')}\n"
    return context

def run_agent(user_query: str):
    print(f"\n[USER]: {user_query}")

    # Step 1: Query Optimization (LLM Call)
    print("[*] Reasoning: Extracting search terms...")
    optimize_prompt = f"Convert this user question into 3-5 high-impact search keywords for a vector database: {user_query}. Output ONLY the keywords separated by spaces."

    headers = {"Authorization": f"Bearer {ANTHROPIC_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": ANTHROPIC_MODEL, "messages": [{"role": "user", "content": optimize_prompt}]}

    try:
        opt_resp = requests.post(f"{ANTHROPIC_BASE_URL}/chat/completions", headers=headers, json=payload)
        search_terms = opt_resp.json()['choices'][0]['message']['content']
        print(f"[*] Optimized Search Query: '{search_terms}'")
    except:
        search_terms = user_query # Fallback

    # Step 2: Execute Local Search
    context = search_qdrant(search_terms)

    if not context:
        print("[!] No relevant documents found.")
        return

    # Step 3: Synthesis (LLM Call)
    print("[*] Synthesis: Generating final report...")
    ...
    prompt = f"""
    You are the Aegis AI Assistant. Use the following internal documents to answer the user's question. 
    If the answer isn't in the documents, say you don't know.

    INTERNAL CONTEXT:
    {context}

    USER QUESTION:
    {user_query}
    """

    headers = {
        "Authorization": f"Bearer {ANTHROPIC_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": ANTHROPIC_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(f"{ANTHROPIC_BASE_URL}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        answer = response.json()['choices'][0]['message']['content']
        print(f"\n[AEGIS]:\n{answer}")
    except Exception as e:
        print(f"[ERROR]: LLM call failed: {e}")

if __name__ == "__main__":
    # Test the loop
    query = "Summarize Jennifer Doudna's discovery mentioned in the documents."
    run_agent(query)
