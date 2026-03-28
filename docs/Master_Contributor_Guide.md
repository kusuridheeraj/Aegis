# Aegis: The Master Contributor & Intern Guide

Welcome to Aegis. This document is the "Source of Truth" for the project's architecture, design decisions, and data flow. It is designed so that anyone can understand the entire system without looking at a single line of code.

---

## 🏛️ 1. The Core Architecture: "Why these tools?"

### Why Apache Kafka? (The Shock Absorber)
In a standard monolith, if a user uploads a 1GB PDF, the server is busy for 30 seconds doing math. If 100 users do this, the server crashes.
*   **Aegis Solution:** We use Kafka to decouple the **Ingestion Gateway** (Java) from the **AI Brain** (Python). 
*   Java's only job is to catch the file and drop a "paper ticket" into Kafka. 
*   Python then picks up that ticket whenever it has free CPU cycles. This prevents the system from ever crashing under load.

### Why MinIO? (The Claim Check Pattern)
We never send the actual file through Kafka. Kafka is for small messages, not 1GB binary blobs.
*   **The Pattern:** Java uploads the file to MinIO, gets a unique `objectId`, and only sends that small ID through Kafka.
*   Python uses the ID to download the file when it's ready. This is called the **Claim Check Pattern**.

### Why Java (Ingestion) and Python (ML)?
*   **Java:** Best-in-class for high-speed I/O, streaming, and enterprise stability. It handles the "plumbing."
*   **Python:** The center of the AI ecosystem. It handles the "intelligence" (LangChain, HuggingFace, LangGraph).

---

## 🔄 2. The Data Lifecycle (End-to-End)

1.  **Detection:** We provide multiple ways to ingest data:
    *   **The File Watcher:** Monitors `input_pdfs/` for real-time streaming.
    *   **The Batch Uploader:** Use `.\scripts\upload_folder.ps1` to ingest entire directories of books.
2.  **Ingestion (Java):** Supports **PDF** and **EPUB** formats. Streams bytes to MinIO and publishes events to Kafka.
3.  **Transformation (Python):**
    *   **PyMuPDF (fitz):** Robust text extraction for both PDFs and EPUBs.
    *   **LangChain:** Semantic chunking using `RecursiveCharacterTextSplitter`.
4.  **Storage:** Vectors are stored in **Qdrant**, our high-performance vector database.
5.  **Garbage Collection:** Once indexed, Python deletes the raw file from MinIO to keep storage costs at $0.

---

## 🧠 3. The AI Layer: Consumption & Autonomy

### How "Tool Calling" Works
We don't just "query" the database. We turn the database into a **Tool** that an LLM (like Claude) can call.
1.  **The Server:** `mcp_server.py` implements the **Model Context Protocol**.
2.  **The Handshake:** When Claude asks, "What is in my docs?", it doesn't know the answer. It sees a "Tool" named `search_documents`.
3.  **The Execution:** Claude sends a JSON request back to our Python server: `{"query": "search query"}`.
4.  **The Retrieval:** Python vectorizes the query, finds the match in Qdrant, and sends the text back to Claude.

### LangChain vs. Naive Code: The "62MB" Lesson
Before LangChain, we used a naive `text.split(" ")`. 
*   **The Failure:** When we uploaded a 10MB binary file, it had no spaces. The code treated it as one massive chunk.
*   **The Bloat:** JSON escaping turned 10MB of binary into 62MB of text, crashing the database.
*   **The LangChain Fix:** `RecursiveCharacterTextSplitter` intelligently monitors chunk size *before* sending it to the model. It ensures every payload is exactly the size the database expects.

### Why LangGraph? (Chains vs. State Machines)
*   **Standard AI (LangChain):** "Search the DB and answer." If the DB search fails, the AI stops. 
*   **Aegis AI (LangGraph):** "Search the DB. Did you find Jennifer Doudna? No? Okay, search for CRISPR instead. Now compile the report."
*   **Autonomy:** LangGraph gives the agent a "memory" and a "loop," allowing it to correct its own mistakes and try multiple search strategies until it finds the truth.

---

## 🛠️ 4. Developer Protocols

*   **Correlation IDs:** Every request is tagged with a UUID that travels from Java -> Kafka -> Python -> Qdrant. This allows us to trace a single file across 3 different languages and 4 different databases.
*   **Quantization (Upcoming):** We squeeze our AI models from 32-bit to 8-bit. This makes them 4x smaller and much faster on standard CPUs without losing accuracy.

**Need Help?** Check the `docs/End_to_End_Testing_Guide.md` to run your first trace!