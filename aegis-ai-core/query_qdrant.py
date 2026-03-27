import json
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Connect to the local Qdrant database
client = QdrantClient(url="http://127.0.0.1:6333")

print("--- Querying Qdrant for 'Linkedin_Posts_2024_Blue.pdf' ---")

# Search for the exact file using a payload filter
results = client.scroll(
    collection_name="aegis_documents",
    scroll_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="object_id",
                match=models.MatchText(text="Linkedin_Posts_2024_Blue.pdf"),
            )
        ]
    ),
    limit=2, # Just show the first 2 chunks so we don't flood the terminal
    with_payload=True,
    with_vectors=False
)

# Print the results nicely
records, next_page_offset = results
if not records:
    print("No records found. Check the object_id.")
else:
    for i, record in enumerate(records):
        print(f"\n[Chunk {i+1} Metadata]")
        print(f"Correlation ID: {record.payload.get('correlation_id')}")
        print(f"Object ID: {record.payload.get('object_id')}")
        print(f"\n[Extracted Text]\n{record.payload.get('text')[:300]}...\n")
        print("-" * 50)
