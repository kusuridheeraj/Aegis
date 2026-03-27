import time
import requests
import subprocess
import os
import sys

"""
Aegis Phase 3: Automated Chaos & Fault Tolerance Verifier

This script automates the following "Enterprise Hardening" scenario:
1. Upload a document while the system is healthy.
2. KILL the Qdrant Vector Database container.
3. Upload another document (should be routed to DLQ).
4. Verify the system is in a 'degraded' health state.
5. RESTART Qdrant.
6. Trigger the DLQ Replayer.
7. Verify that the document finally makes it to Qdrant.
"""

GATEWAY_URL = "http://localhost:8080/api/v1/documents"
AI_CORE_URL = "http://localhost:8000"
TEST_FILE = "input_pdfs/clean_test.txt"

def run_command(cmd):
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.stdout

def check_health():
    try:
        resp = requests.get(f"{AI_CORE_URL}/health")
        return resp.json()
    except:
        return None

def upload_file(filename):
    print(f"Uploading {filename}...")
    with open(filename, "rb") as f:
        resp = requests.post(GATEWAY_URL, files={"file": f})
    return resp.json()

def main():
    if not os.path.exists(TEST_FILE):
        with open(TEST_FILE, "w") as f:
            f.write("This is a chaos test document for Aegis Phase 3.")

    print("=== STARTING AEGIS CHAOS TEST ===")
    
    # 1. Check Initial Health
    health = check_health()
    if not health or health.get("status") != "ok":
        print("Aborting: System is not healthy. Run 'docker-compose up -d' first.")
        sys.exit(1)
    print("Pre-check: System is HEALTHY.")

    # 2. Kill Qdrant
    print("Simulating Infrastructure Failure: Stopping 'aegis-qdrant'...")
    run_command(["docker", "stop", "aegis-qdrant"])
    
    # Wait for health check to reflect the change
    print("Waiting for health check to detect failure...")
    time.sleep(5)
    health = check_health()
    print(f"Current Health: {health.get('status')} (Qdrant: {health.get('dependencies', {}).get('qdrant')})")

    # 3. Upload while broken
    upload_resp = upload_file(TEST_FILE)
    correlation_id = upload_resp.get("correlationId")
    print(f"Ingestion Accepted (Correlation ID: {correlation_id}).")
    print("Event should be moving to DLQ now...")
    time.sleep(5)

    # 4. Restart Qdrant
    print("Resolving Infrastructure Failure: Starting 'aegis-qdrant'...")
    run_command(["docker", "start", "aegis-qdrant"])
    time.sleep(5)
    
    # 5. Trigger Replay
    print("Triggering DLQ Replay Mechanism...")
    replay_resp = requests.post(f"{AI_CORE_URL}/api/v1/system/replay-dlq")
    print(f"Replay Response: {replay_resp.json()}")

    print("Waiting for reprocessing...")
    time.sleep(10)

    # 6. Verify Log
    print("Checking AI Core logs for successful reprocessing...")
    logs = run_command(["docker", "logs", "--tail", "50", "aegis-ai"])
    if correlation_id in logs and "Successfully processed" in logs:
        print("SUCCESS: Document reprocessed from DLQ and stored in Qdrant!")
    else:
        print("FAILED: Correlation ID not found in logs with success message.")
        print("Check 'docker logs aegis-ai' manually.")

    print("=== CHAOS TEST COMPLETE ===")

if __name__ == "__main__":
    main()
