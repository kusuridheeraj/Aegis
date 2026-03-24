import pytest
from services.embedding_service import chunk_text, generate_embeddings, extract_text_from_pdf

def test_chunk_text():
    # Generate exactly 1000 words
    dummy_text = "word " * 1000
    
    # We expect 500 word chunks with a 50 word overlap
    chunks = chunk_text(dummy_text, chunk_size=500, overlap=50)
    
    # Chunk 1: words 0-500
    # Chunk 2: words 450-950
    # Chunk 3: words 900-1000
    assert len(chunks) == 3
    assert len(chunks[0].split()) == 500
    assert len(chunks[1].split()) == 500
    assert len(chunks[2].split()) == 100

def test_generate_embeddings_dimensions():
    dummy_chunks = ["This is the first test chunk.", "This is the second test chunk."]
    
    embeddings = generate_embeddings(dummy_chunks)
    
    # We passed in 2 chunks, we should get 2 vectors back
    assert len(embeddings) == 2
    
    # The all-MiniLM-L6-v2 model must ALWAYS return exactly 384 dimensions
    assert len(embeddings[0]) == 384
    assert type(embeddings[0][0]) == float

def test_extract_text_fallback():
    # If we pass a random binary string instead of a PDF, it should fallback gracefully
    binary_data = b"This is not a real PDF"
    text = extract_text_from_pdf(binary_data)
    assert text == "This is not a real PDF"
