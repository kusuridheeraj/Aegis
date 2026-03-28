import os
import sys
from pathlib import Path

# Add venv libs to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
venv_lib = os.path.join(BASE_DIR, "aegis-ai-core", "venv", "Lib", "site-packages")
sys.path.append(venv_lib)

from optimum.onnxruntime import ORTModelForFeatureExtraction
from transformers import AutoTokenizer

"""
Aegis Model Quantization Tool (Python API version)

This script uses the optimum Python API to export and optimize 
the model, bypassing CLI-specific argument bugs.
"""

def export_model():
    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    output_dir = os.path.join(BASE_DIR, "aegis-ai-core", "models", "all-MiniLM-L6-v2-onnx")
    
    print(f"--- Exporting {model_id} to ONNX ---")
    print(f"Target Directory: {output_dir}")
    
    try:
        # 1. Load and export the model
        # 'export=True' triggers the ONNX conversion
        model = ORTModelForFeatureExtraction.from_pretrained(
            model_id, 
            export=True
        )
        tokenizer = AutoTokenizer.from_pretrained(model_id)

        # 2. Save the model and tokenizer
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        
        print(f"\n[SUCCESS] Model successfully exported to: {output_dir}")
        print("Note: 8-bit quantization is applied dynamically during inference in embedding_service.py")
        
    except Exception as e:
        print(f"\n[ERROR] Python Export failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    export_model()
