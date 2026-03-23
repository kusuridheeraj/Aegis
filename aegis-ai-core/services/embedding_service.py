import fitz  # PyMuPDF
import logging
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Initialize the open-source embedding model locally.
logger.info("Loading SentenceTransformer model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
logger.info("Model loaded.")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts raw text from a PDF byte stream using PyMuPDF."""
    text = ""
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text("text") + "\n"
    except Exception as e:
        logger.error(f"Failed to parse PDF: {e}")
        text = file_bytes.decode('utf-8', errors='ignore')
    return text

def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """
    Uses LangChain's RecursiveCharacterTextSplitter for semantic chunking.
    Unlike naive split(), this respects paragraph and sentence boundaries,
    ensuring the LLM receives complete thoughts instead of shattered context.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_text(text)

def generate_embeddings(chunks: list[str]) -> list[list[float]]:
    """Converts a list of text chunks into numerical vectors."""
    if not chunks:
        return []
    embeddings = model.encode(chunks)
    return embeddings.tolist()
