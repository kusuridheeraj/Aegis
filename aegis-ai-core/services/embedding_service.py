import fitz  # PyMuPDF
import logging
import time
import os
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Initialize the embedding model.
# Hybrid Loading logic: Use Quantized ONNX if available, otherwise standard PyTorch.
os.environ["TRANSFORMERS_OFFLINE"] = "1"
ONNX_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "all-MiniLM-L6-v2-onnx")

logger.info("Initializing Aegis Embedding Engine...")

if os.path.exists(ONNX_PATH):
    try:
        from optimum.onnxruntime import ORTModelForFeatureExtraction
        from transformers import AutoTokenizer, pipeline
        
        logger.info(f"Loading 8-bit Quantized Model from {ONNX_PATH}...")
        tokenizer = AutoTokenizer.from_pretrained(ONNX_PATH)
        onnx_model = ORTModelForFeatureExtraction.from_pretrained(ONNX_PATH)
        
        # Wrap in a simple interface that matches SentenceTransformer.encode
        class QuantizedTransformer:
            def __init__(self, model, tokenizer):
                self.pipeline = pipeline("feature-extraction", model=model, tokenizer=tokenizer)
            
            def encode(self, sentences):
                # Returns the mean of the embeddings for the sentence
                import torch
                outputs = self.pipeline(sentences)
                # Convert to list of lists
                return [torch.tensor(o).mean(dim=1).squeeze().tolist() for o in outputs]

        model = QuantizedTransformer(onnx_model, tokenizer)
        logger.info("INT8 Quantized Model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load Quantized model: {e}. Falling back to standard.")
        model = SentenceTransformer('all-MiniLM-L6-v2')
else:
    logger.info("No quantized model found. Loading standard precision SentenceTransformer.")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully from local cache.")
    except Exception as e:
        logger.warning(f"Local model load failed, attempting download: {e}")
        os.environ["TRANSFORMERS_OFFLINE"] = "0"
        model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extracts raw text based on the file type."""
    text = ""
    filename_lower = filename.lower()
    
    try:
        if filename_lower.endswith(".pdf"):
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text("text") + "\n"
        else:
            # For .md, .log, .py, .java, .csv, .txt, etc.
            raw_content = file_bytes.decode('utf-8', errors='ignore')
            text = f"File Path Context: {filename}\n\n{raw_content}"
    except Exception as e:
        logger.error(f"Failed to extract text from {filename}: {e}")
        text = file_bytes.decode('utf-8', errors='ignore')
        
    # Prepend filename for PDFs too if it succeeded
    if text and filename_lower.endswith(".pdf"):
        text = f"Source Document: {filename}\n\n{text}"
        
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
