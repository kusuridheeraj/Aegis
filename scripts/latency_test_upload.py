import time
import requests
import sys
import os

"""
Aegis Precision Latency Tester

This script is provided to bypass OS-level bugs found in Windows 'curl.exe' 
when handling filenames with commas or parentheses. 

It is also used to benchmark the exact millisecond latency of the Spring Boot 
Claim Check pattern under heavy load.
"""

def test_upload(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
        
    print(f"Uploading '{os.path.basename(file_path)}' to Java Gateway...")
    
    start = time.time()
    try:
        # We explicitly omit the content-type so the Java Gateway relies on its 
        # fallback mechanisms, proving backend resilience.
        with open(file_path, "rb") as f:
            response = requests.post("http://localhost:8080/api/v1/documents", files={"file": f})
        
        end = time.time()
        
        print("-" * 40)
        print(f"Status Code: {response.status_code}")
        
        try:
            data = response.json()
            print(f"Correlation ID: {data.get('correlationId')}")
            print(f"Message: {data.get('message')}")
        except:
            print(f"Raw Response: {response.text}")
            
        print("-" * 40)
        # Multiply by 1000 to get milliseconds
        latency = int((end - start) * 1000)
        print(f"Gateway Ingestion Latency: {latency} ms")
        print("-" * 40)
        
        if response.status_code == 202:
            print("SUCCESS: File successfully handed off to Kafka. Check 'docker logs -f aegis-ai' for processing metrics.")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to http://localhost:8080. Is the aegis-gateway container running?")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python latency_test_upload.py <path_to_file>")
        sys.exit(1)
    
    test_upload(sys.argv[1])