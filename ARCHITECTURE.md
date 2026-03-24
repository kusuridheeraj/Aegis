# Project Aegis: Architecture Decision Records (ADR)

This document serves as the definitive guide to the architectural choices, trade-offs, and design patterns utilized in **Project Aegis**. As an open-source Enterprise RAG (Retrieval-Augmented Generation) Engine, Aegis is built on first principles of distributed systems design. 

For every major component, we evaluated the "standard" or naive approach against the enterprise requirements of high availability, fault tolerance, and cost efficiency.

---

## 1. The Ingestion Edge: Java/Spring Boot vs. Python/FastAPI

**The Requirement:** Accept incoming 1GB+ document payloads without crashing the web server or dropping concurrent connections.

**The Naive Approach (The Monolith):**
Build a single Python FastAPI application that accepts the file upload, processes the text, generates vectors, and saves to the database in a single synchronous thread.
* *Why it fails:* Vector generation (ML) is strictly CPU-bound. Network ingestion is strictly I/O-bound. Python's Global Interpreter Lock (GIL) and single-threaded event loop mean that if a massive PDF triggers a CPU-heavy embedding task, the web server thread pool will stall, causing all other incoming HTTP requests to time out.

**The Aegis Architecture (Polyglot Microservices):**
We split the system. The edge gateway is written in Java (Spring Boot). The JVM and Tomcat are uniquely optimized for handling thousands of concurrent I/O-bound network connections. Spring Boot utilizes the **Claim Check Pattern**: it streams the binary payload directly to MinIO in 8KB chunks (keeping heap usage flat at ~250MB), grabs a lightweight `objectId`, and passes that token to the downstream system.

---

## 2. The Event Bus: Apache Kafka vs. Direct HTTP Streams

**The Requirement:** Pass the ingestion token from Java to the Python processing worker.

**The Naive Approach (Synchronous REST):**
Spring Boot makes a synchronous HTTP POST request to the internal Python FastAPI worker: `POST /process { "objectId": "123.pdf" }`.
* *Why it fails:* Tight coupling. If the Python worker is offline, deploying, or crashes due to a corrupted PDF, the HTTP request fails. The Java gateway either has to implement complex exponential backoff retries, or the user's data is permanently lost.

**The Aegis Architecture (Asynchronous Event Bus):**
We introduced **Apache Kafka**. Spring Boot drops a 200-byte JSON event into the `aegis.documents.raw` topic and instantly returns a `202 Accepted` to the client. 
* *Validation:* Kafka acts as a shock absorber. If the Python ML worker goes down, Java is completely unaffected. The events queue up safely in Kafka. When Python restarts, it reads the committed offsets and resumes exactly where it left off. Zero data loss.

---

## 3. Text Extraction: LangChain vs. Native String Splitting

**The Requirement:** Break a 150,000-word document into digestible chunks for the LLM's context window.

**The Naive Approach (Native Splitting):**
Read the file into memory and use `text.split(" ")` to chop the document blindly every 500 words.
* *Why it fails:* Blind chunking destroys semantic meaning. A 500-word hard stop will frequently chop a sentence or a critical paragraph exactly in half. When an LLM retrieves half a sentence from the vector database, it lacks context and hallucinates the rest.

**The Aegis Architecture (Semantic Chunking):**
We implemented **LangChain's `RecursiveCharacterTextSplitter`**. 
* *Validation:* Instead of counting words, LangChain intelligently evaluates the structure of the document. It attempts to split on double newlines (paragraphs) first, then single newlines, then spaces. This ensures that the boundaries of the chunks align with the author's original semantic intent, vastly improving the accuracy of the final RAG retrieval.

---

## 4. Vector Storage: Qdrant vs. PostgreSQL (pgvector)

**The Requirement:** Store hundreds of thousands of 384-dimensional mathematical arrays and perform sub-millisecond cosine similarity searches.

**The Naive Approach (RDBMS Extension):**
Deploy a massive PostgreSQL database and install the `pgvector` extension.
* *Why it fails:* PostgreSQL is a relational database. It utilizes immense RAM and CPU overhead to maintain ACID compliance, transaction logs (WAL), and relational table locks. Vector embeddings are immutable mathematical arrays; they do not require relational ACID overhead.

**The Aegis Architecture (Dedicated Vector Engine):**
We deployed **Qdrant**.
* *Validation:* Written entirely in Rust, Qdrant is purpose-built for vector search. It utilizes a highly optimized HNSW (Hierarchical Navigable Small World) graph algorithm. It achieves higher throughput and lower search latency on a fraction of the hardware footprint (and cost) required by an RDBMS.

---

## 5. The AI Interface: LangGraph & MCP vs. Chatbot GUIs

**The Requirement:** Allow AI agents to query the Vector Database to answer user questions.

**The Naive Approach (Proprietary REST API & GUI):**
Build a custom REST endpoint `/api/search` and rely on a consumer GUI (like ChatGPT or Claude Desktop) to manually hit the endpoint.
* *Why it fails:* Vendor lock-in and lack of autonomy. If you build a custom REST API, you have to write proprietary integration code for every new LLM that hits the market. Furthermore, relying on a GUI means the system cannot perform automated background tasks (like nightly cron-job intelligence reports).

**The Aegis Architecture (MCP + LangGraph):**
1. **The Boundary:** We exposed the database using Anthropic's open-source **Model Context Protocol (MCP)**. This turns Aegis into a universal "socket." Any AI client (Claude, Cursor, Gemini) that supports MCP can natively connect and query the data without us writing custom integration logic.
2. **The Autonomous Agent:** We built a headless state machine using **LangGraph** (`agent.py`). 
* *Validation:* LangGraph allows us to build programmatic, multi-step agentic workflows. Our agent can wake up, query the MCP server, cross-reference data, and generate reports entirely asynchronously, freeing us from the limitations of consumer-facing chat interfaces.

---

## 6. Enterprise Hardening: Tracing & DLQs

**The Requirement:** Ensure system observability and prevent data loss during extraction failures.

**The Aegis Architecture:**
* **Distributed Tracing:** Java generates a `UUID` Correlation ID at the edge. It is passed into Kafka, logged by Python, and stored in Qdrant. This allows ops teams to `grep` logs across multiple isolated containers to track the lifecycle of a single document.
* **Dead Letter Queues (DLQ):** If Python fails to process a document (e.g., Qdrant network timeout), a custom Kafka Producer catches the exception and routes the original event + stack trace to `aegis.documents.failed`. This guarantees that transient infrastructure failures never result in the silent loss of user data.