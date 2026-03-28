import time
import psutil
import os
import sys
from sentence_transformers import SentenceTransformer

# Add AI core to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, 'aegis-ai-core'))

def get_mem_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # MB

def run_benchmark():
    from services.embedding_service import ONNX_PATH
    
    # Use 100 chunks for a faster benchmark
    test_text = "The quick brown fox jumps over the lazy dog."
    test_chunks = [test_text] * 100 
    
    print("\n--- Aegis Quantization Benchmark ---")
    print(f"Testing with {len(test_chunks)} text chunks...")

    # --- 1. Standard FP32 Benchmark ---
    print("\n[1/2] Benchmarking Standard Model (FP32)...")
    start_mem = get_mem_usage()
    model_std = SentenceTransformer('all-MiniLM-L6-v2')
    start_time = time.time()
    model_std.encode(test_chunks)
    std_duration = time.time() - start_time
    load_mem = get_mem_usage() - start_mem
    
    print(f"FP32 RAM Usage: {load_mem:.2f} MB")
    print(f"FP32 Processing Time: {std_duration:.2f} seconds")

    # --- 2. 8-bit Quantized Benchmark ---
    print("\n[2/2] Benchmarking 8-bit Quantized Model (INT8 via ONNX)...")
    
    try:
        from optimum.onnxruntime import ORTModelForFeatureExtraction
        from transformers import AutoTokenizer
        import torch
        
        # Load ONNX version
        tokenizer = AutoTokenizer.from_pretrained(ONNX_PATH)
        onnx_model = ORTModelForFeatureExtraction.from_pretrained(ONNX_PATH)
        
        start_mem_q = get_mem_usage()
        start_time_q = time.time()
        
        # Optimized Batch Inference
        encoded_input = tokenizer(test_chunks, padding=True, truncation=True, return_tensors="pt")
        with torch.no_grad():
            model_output = onnx_model(**encoded_input)
        
        # Perform mean pooling efficiently
        attention_mask = encoded_input['attention_mask']
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        final_vectors = sum_embeddings / sum_mask
        
        quant_duration = time.time() - start_time_q
        quant_mem = get_mem_usage() - start_mem_q
        
        print(f"INT8 RAM Usage: {quant_mem:.2f} MB")
        print(f"INT8 Processing Time: {quant_duration:.2f} seconds")
        
        print("\n--- FINAL METRICS COMPARISON ---")
        print(f"Speedup: {((std_duration/quant_duration)):.1f}x faster")
        print(f"RAM Savings: {((1 - quant_mem/load_mem)*100):.0f}% reduction")
        
    except Exception as e:
        print(f"[!] Quantized run failed: {e}")

if __name__ == "__main__":
    run_benchmark()
