# Testing Aegis: End-to-End Execution Guide

Aegis is a fully containerized, asynchronous Enterprise RAG pipeline. This guide provides step-by-step instructions to test the entire architecture—from the Spring Boot Gateway edge to the Python ML worker and the Qdrant Vector database.

---

## Step 1: Boot the Cluster

Because Aegis is fully containerized, you do not need to manually install Java or Python on your host machine to run the system.

1. Ensure **Docker Desktop** is running.
2. Open a terminal in the root of the repository and run:
   ```bash
   docker-compose down -v --remove-orphans
   docker-compose up -d --build
   ```
*(Note: The first build may take a minute as it caches the Maven and Python libraries. Subsequent builds will take ~3 seconds).*

Verify all 6 containers are `Up (healthy)` by running `docker ps`. 

---

## Step 2: Ingest Data (Two Methods)

We provide two distinct methods for feeding data into the Aegis engine.

### Option A: The Real-Time File Watcher (For Codebases & Batch PDFs)
We wrote a background daemon that monitors a folder and instantly streams any new file to the API, bypassing Windows `curl` bugs.
1. Run the watcher script in a terminal:
   ```powershell
   .\scripts\watch_folder.ps1 -FolderPath ".\input_pdfs"
   ```
2. Drag and drop any `.pdf`, `.java`, `.py`, or `.md` file into the `input_pdfs/` folder. The watcher will instantly fire it into the pipeline.

### Option B: The Precision Latency Tester (For Benchmarking)
To prove the Spring Boot **Claim Check** pattern bypasses the JVM heap and achieves millisecond latency (even on 40MB+ files), use our custom Python benchmark script:
```bash
cd aegis-ai-core
.\venv\Scripts\python.exe ..\scripts\latency_test_upload.py "..\input_pdfs\your_massive_file.pdf"
```
This script explicitly measures the exact HTTP request round-trip time.

---

## Step 3: The Trace Matrix (Reading the Logs)

Once a file is uploaded, you can trace its exact lifecycle across the microservices using Docker logs.

1. **The Ingestion Edge (Java):**
   ```bash
   docker logs --tail 20 aegis-gateway
   ```
   *Look for:* The `Gateway Ingestion Latency` metric in your terminal or the `Published event to Kafka` log. It should be under 1.5 seconds, even for a massive payload.

2. **The ML Worker (Python):**
   ```bash
   docker logs -f aegis-ai
   ```
   *Look for:* The HuggingFace progress bar. It will tell you exactly how many semantic chunks LangChain generated, and exactly how many seconds it took the CPU to compute the 384-dimensional mathematical vectors.

3. **Garbage Collection:**
   At the very end of the Python log, you must see:
   `Embeddings complete. Purged raw binary from MinIO.`
   This proves the system deleted the raw file from cloud storage after vectorization to prevent disk bloat.

---

## Step 4: Verify the Database (Qdrant)

To prove the AI vectors and textual metadata actually survived the distributed journey, query the database directly:

1. Open `aegis-ai-core/query_qdrant.py` and modify the `MatchText` string to match the name of the file you just uploaded.
2. Run the query script:
   ```bash
   cd aegis-ai-core
   .\venv\Scripts\python.exe query_qdrant.py
   ```
It will connect to Qdrant and print out the exact English text paragraphs retrieved from the vector index, tagged with the distributed `Correlation ID`.

---

## Step 5: Unit Testing the ML Logic

The Python application includes a `pytest` suite that explicitly verifies the mathematical dimensions of the HuggingFace embeddings and the fallback mechanisms for the LangChain chunker.

To run the test suite locally:
```bash
cd aegis-ai-core
.\venv\Scripts\pytest tests/ -v
```

---

## Step 6: System Reset

If you have uploaded massive gigabytes of data and want to wipe the slate clean, simply destroy the Docker volumes:
```bash
docker-compose down -v
```
This permanently deletes the MinIO, Kafka, and Qdrant storage volumes, returning your infrastructure to 0 bytes.