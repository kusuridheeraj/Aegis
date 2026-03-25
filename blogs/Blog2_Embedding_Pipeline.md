# The 62MB JSON Payload: Surviving Database Outages with Semantic Chunking and Dead Letter Queues

In Part 1 of this series, I broke down how **Aegis**—an enterprise Retrieval-Augmented Generation (RAG) engine—uses the Claim Check pattern in Spring Boot to ingest 1GB+ documents with a flat ~250MB heap footprint. 

The Java gateway streams the binary payload to MinIO and drops a lightweight event token into Apache Kafka. 

But getting massive files *into* a distributed system safely is only half the battle. Processing them asynchronously across language barriers (Java to Python) introduces a completely new set of bottlenecks. 

Here is the story of how a 10MB test file silently destroyed user data, and how I hardened the Python AI worker using LangChain, Kafka Dead Letter Queues, and Chaos Engineering.

---

### The Catastrophe: The 62MB Payload Bug

When the Python worker reads the Kafka event, it uses the `objectId` to download the document from MinIO into memory and extracts the text using `PyMuPDF`. 

Initially, to prepare the text for the HuggingFace embedding model (`all-MiniLM-L6-v2`), I wrote a naive Python function that split the document every 500 words using `text.split(" ")`. 

To stress-test the worker, I generated a 10MB dummy binary file and uploaded it. The pipeline immediately crashed, and the Qdrant vector database threw a `400 Bad Request`:
`Payload error: JSON payload (62922836 bytes) is larger than allowed (limit: 33554432 bytes).`

**How did 10MB become 62MB?** 
Because the dummy file was raw binary zeros, it contained no spaces. My naive `.split(" ")` function treated the entire 10MB file as one massive "word." 

Qdrant's REST API requires a JSON payload. JSON is strictly a text format; it cannot natively hold raw binary null bytes. When Python's `json.dumps()` attempted to serialize 10 million non-printable binary null bytes, it panicked and escaped every single one of them into the Unicode string `\u0000`. 

Let's do the math on that unicode string:
* `\` (1 byte)
* `u` (1 byte)
* `0` (1 byte)
* `0` (1 byte)
* `0` (1 byte)
* `0` (1 byte)

To safely represent a single **1-byte** null character in JSON text, the system had to use **6 bytes** of text. 
`10MB * 6 = 60MB.`

Add in the standard JSON brackets, HTTP headers, the 384-dimensional vector array numbers, and the metadata, and the payload hit exactly **62,922,836 bytes**. The escaped string bloated past Qdrant's strict 32MB HTTP request limit, and the database violently severed the TCP connection.

**The Silent Data Loss**
The database rejecting the payload was bad. But the *real* catastrophe was what happened next. Because I was relying on a standard `try/except` block and Kafka's `enable_auto_commit=True`, the Python script logged the error and moved on. Kafka assumed the message was processed successfully and advanced the offset.

That user's 10MB document was silently lost forever. 

In a production enterprise environment, silently dropping a corporate document during vectorization means you have permanently corrupted the integrity of the search index.

---

### The Fix Part 1: Semantic Chunking (LangChain)

Naive chunking is an anti-pattern. Even if a document isn't binary, blindly chopping sentences in half destroys the context the LLM needs, leading directly to AI hallucinations.

To prevent un-chunkable strings and preserve data quality, I ripped out the custom logic and integrated **LangChain**.

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_text(text)
```

By using the `RecursiveCharacterTextSplitter`, the system now attempts to split by double newlines (paragraphs) first, then single newlines. This guarantees predictable payload sizes and preserves the semantic boundaries of the author's original thoughts.

---

### The Fix Part 2: The Dead Letter Queue (DLQ)

To solve the silent data loss, I had to design for catastrophic failure. If the Qdrant database goes down, or an extraction times out, we cannot afford to drop the Kafka message. 

I implemented a Kafka **Dead Letter Queue (DLQ)** producer in the Python worker. 

```python
        except Exception as e:
            error_details = str(e)
            logger.error(f"[{correlation_id}] Failed to process document {object_id}: {error_details}")
            send_to_dlq(correlation_id, event, error_details)
```

Now, any failed chunking or embedding task automatically catches the exception, wraps the original JSON event, the exact stack trace, and the distributed tracing `Correlation ID`, and pushes it to an `aegis.documents.failed` topic. Ops teams can monitor this topic, fix the database, and replay the exact events. Zero data loss.

---

### The Proof: A Live Chaos Test

An architecture is only theoretical until you try to break it. I ran a live Chaos Engineering test on the local Docker cluster to prove the DLQ worked. 

1. I initiated a file upload to the Spring Boot gateway.
2. While the file was streaming to MinIO, I intentionally ran `docker stop aegis-qdrant` to kill the vector database mid-flight, simulating a sudden network drop. 
3. Python successfully downloaded the file, chunked it, generated the 384-dimensional vectors in ~4.5 seconds, and attempted the database upsert. 
4. The logs threw the expected crash: `[WinError 10061] No connection could be made because the target machine actively refused it`.

Because of the new architecture, the DLQ caught it instantly. I queried the `aegis.documents.failed` topic, and the payload was sitting there perfectly intact, waiting for the database to come back online. 

> **Sidebar: Two Lessons in Distributed Systems**
> **1. The IPv6 Flap:** Wiring Python to Kafka inside a Docker bridge network exposed a classic networking bug. My Python logs showed `connecting to localhost:9092 [IPv6 ('::1')]` followed by an immediate drop. Kafka's `ADVERTISED_LISTENERS` was set to `localhost`. Python resolved `localhost` to IPv6 `::1`, but the Java KRaft controller was strictly bound to IPv4. The protocol mismatch caused a silent drop. I fixed it by forcing the listener to `127.0.0.1`. 
> 
> **2. The Unkillable Thread:** During local testing, attempting to stop the FastAPI server (`CTRL+C`) caused the terminal to hang indefinitely, eventually throwing `ValueError: Invalid file descriptor: -1`. To prevent the blocking `for message in consumer:` loop from starving the web server, I launched it inside `asyncio.get_event_loop().run_in_executor()`. However, when Uvicorn receives a SIGINT (`CTRL+C`) to gracefully shut down, it waits for all background threads to finish. Because the Kafka thread is trapped in an infinite network-polling loop, it ignores the shutdown signal, resulting in a hung process until the OS forcefully rips the sockets away. In production, this requires passing a `threading.Event()` kill switch to the loop. 
> 
> *Never hide your failures; they are the best teachers.*

### Next Steps

The backend pipeline is now fully hardened, asynchronous, and fault-tolerant. 

In the final post of this series, I will decouple Aegis from consumer chatbot GUIs (like Claude Desktop) by implementing Anthropic's **Model Context Protocol (MCP)** and building a headless **LangGraph** state machine to query the system autonomously.

You can review the dual-stack architecture and the automated test suite on my GitHub:
🔗 **[Aegis Repository](https://github.com/kusuridheeraj/Aegis)**