import fitz  # PyMuPDF
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Initialize the open-source embedding model locally.
# all-MiniLM-L6-v2 is fast, lightweight, and perfect for testing RAG.
# It produces vectors of 384 dimensions.
logger.info("Loading SentenceTransformer model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
logger.info("Model loaded.")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts raw text from a PDF byte stream using PyMuPDF."""
    text = ""
    try:
        # Open PDF from memory
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text("text") + "\n"
    except Exception as e:
        logger.error(f"Failed to parse PDF: {e}")
        # Fallback to decode as simple text if it's not a PDF (e.g., our test .bin files)
        text = file_bytes.decode('utf-8', errors='ignore')
    return text

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits a large document into smaller, semantic chunks.
    Overlapping ensures context isn't lost at the boundaries.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def generate_embeddings(chunks: list[str]) -> list[list[float]]:
    """Converts a list of text chunks into numerical vectors."""
    if not chunks:
        return []
    embeddings = model.encode(chunks)
    return embeddings.tolist()
