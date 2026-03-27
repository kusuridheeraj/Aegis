import time
import os
import psutil
import torch
from sentence_transformers import SentenceTransformer
from fast_sentence_transformers import FastSentenceTransformer

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # Convert to MB

def benchmark_model(model_name, model_class, chunks, is_quantized=False):
    print(f"\n--- Benchmarking: {model_name} (Quantized={is_quantized}) ---")
    
    start_mem = get_memory_usage()
    
    # Load model
    start_load = time.time()
    if is_quantized:
        model = model_class('all-MiniLM-L6-v2', device='cpu', quantize=True)
    else:
        model = model_class('all-MiniLM-L6-v2')
    load_time = time.time() - start_load
    
    after_load_mem = get_memory_usage()
    model_mem = after_load_mem - start_mem
    
    # Warm up
    model.encode(["Warm up text"])
    
    # Benchmark Inference
    start_inf = time.time()
    embeddings = model.encode(chunks)
    inf_time = time.time() - start_inf
    
    print(f"Model Load Time: {load_time:.2f}s")
    print(f"RAM Usage: {model_mem:.2f} MB")
    print(f"Inference Time ({len(chunks)} chunks): {inf_time:.4f}s")
    print(f"Avg Time per Chunk: {(inf_time/len(chunks))*1000:.2f}ms")
    
    return {
        "load_time": load_time,
        "mem": model_mem,
        "inf_time": inf_time
    }

if __name__ == "__main__":
    # Sample text chunks (Simulating a medium-sized document)
    test_chunks = ["Aegis is a distributed enterprise RAG engine."] * 100
    
    print("Starting Aegis Quantization Benchmark...")
    
    # 1. Standard Precision
    std_results = benchmark_model("Standard-Transformer", SentenceTransformer, test_chunks, False)
    
    # 2. 8-bit Quantized
    quant_results = benchmark_model("Fast-Quantized-Transformer", FastSentenceTransformer, test_chunks, True)
    
    print("\n" + "="*40)
    print("         FINAL COMPARISON           ")
    print("="*40)
    speedup = std_results['inf_time'] / quant_results['inf_time']
    mem_saving = std_results['mem'] - quant_results['mem']
    
    print(f"Inference Speedup: {speedup:.2x} faster")
    print(f"RAM Savings: {mem_saving:.2f} MB")
    print("="*40)
