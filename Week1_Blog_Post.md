# The 2GB Payload Problem: Dropping API Latency from 32s to 12ms using the Claim Check Pattern

If you ask an AI or a junior engineer how to handle a file upload in Spring Boot, they’ll give you the same answer: grab the `MultipartFile`, call `.getBytes()`, and save it. 

When you're dealing with a 50KB profile picture, that works. But when you are building an Enterprise system tasked with ingesting massive documents or millions of telemetry logs? **That synchronous approach will cause a JVM death spiral.**

This week, while building the ingestion gateway for **Project Aegis** (a distributed enterprise RAG engine), I needed to prove exactly *why* naive uploads fail under load, and how to architect a system that physically cannot run out of memory. 

I didn't just read about it. I built it, benchmarked it on my local machine, and here is exactly what the data showed.

---

### The Experiment: The 4GB Heap Limit

My development machine has 16GB of physical RAM. By default, Spring Boot automatically provisions a Max Heap Size (`MaxHeapSize`) of 1/4th of physical memory, giving my JVM a hard ceiling of ~4GB.

I built a standard, synchronous Spring Boot REST endpoint using the naive `file.getBytes()` method, and then built a decoupled endpoint using the **Claim Check Pattern**. 

I then blasted both endpoints with 1GB payloads. Here is the brutal reality:

| Metric | Synchronous (Naive `.getBytes()`) | Claim Check (Aegis Architecture) |
| :--- | :--- | :--- |
| **1x 1GB File Upload** | 32.4 seconds (Success) | **12 milliseconds** (Returns HTTP 202) |
| **3x 1GB Concurrent** | `OutOfMemoryError` (HTTP 500) | **18 milliseconds** (Success) |
| **6x 1GB Barrage** | Instant JVM Crash | **Flat at ~250MB Heap** (Success) |

#### Why the Naive Approach Failed
When you upload a single 1GB file using the naive approach, the JVM allocates a contiguous 1GB block in the heap. Since my Max Heap is 4GB, it handled a single file fine. But during the concurrent test, the endpoint tried to allocate 3GB+ of heap simultaneously. Combined with Spring Boot's baseline memory and Tomcat thread overhead, it hit the ceiling and instantly threw an `OutOfMemoryError`.

---

### The Architecture: How the Claim Check Works

To solve this, I implemented the Claim Check pattern. Think of it like a coat check at a museum. You don't carry your heavy coat around the exhibits. You hand it to the attendant, they lock it in a closet, and they hand you a lightweight paper ticket. 

Here is exactly what changed in the code to bypass the heap entirely:

Instead of calling `.getBytes()`, my Spring Boot Gateway opens an `InputStream` and **streams** the data directly into a local MinIO (S3-compatible) object store. 

Instead of reading all 1GB into memory at once, the system reads the incoming network request in tiny chunks (e.g., 8KB at a time), writes that chunk to MinIO, discards the chunk, and reads the next one. **Result: Streaming a 10MB file uses ~8KB of heap. Streaming a 5GB file uses the exact same ~8KB of heap.**

1. **The Secure Closet (MinIO):** The file streams to MinIO, bypassing the JVM. MinIO generates a unique `objectId`.
2. **The Paper Ticket (Kafka):** The Spring Boot app takes this `objectId` and publishes a tiny `DocumentIngestedEvent` (a few bytes of JSON) to an **Apache Kafka** topic (`aegis.documents.raw`). 
3. **The Instant Release:** The moment the event hits Kafka, the gateway returns an HTTP `202 Accepted`. 

---

### Why This Matters in the Real World

This is a core concept that separates standard development from Staff-level architecture:

1. **Cost:** By keeping the heap usage flat at ~250MB regardless of file size, organizations don't need to throw 256GB RAM servers at an API. They can run this API on tiny, cheap 512MB Docker containers in Kubernetes, scaling them horizontally infinitely.
2. **Blast Radius Reduction:** In the naive approach, if one user uploads a massive 4K video, they crash the JVM, taking down the API for everyone else currently connected to that node. With Claim Check, huge files never threaten JVM stability.
3. **Decoupling:** Once the file is in MinIO and the event is in Kafka, 5 different downstream services (AI indexing, Virus scanning, Thumbnail generation) can all process that file independently, at their own speed, without hanging the user's browser window.

### The Staff-Level Horizon: Scaling to 10 Million Hits/Sec

The Claim Check pattern handles standard enterprise traffic flawlessly. But what if we needed to handle **10 million concurrent 1GB uploads**? 

At that scale, pushing 10 Petabytes of bandwidth through your Spring Boot servers will fry your Network Interface Cards (NICs), regardless of memory efficiency. 

To survive that, you must evolve the architecture again to use **Direct-to-S3 Pre-Signed URLs**. The client asks Spring Boot for a cryptographic URL, and the client uploads the 1GB file *directly* to the cloud storage bucket, completely bypassing the application servers. The storage bucket then triggers the Kafka event natively. 

If you are transitioning from standard feature development to building high-availability distributed systems, you can pull my raw architecture, the Docker infrastructure, and the benchmark configurations for Project Aegis on my GitHub here: 

🔗 **[https://github.com/kusuridheeraj/Aegis](https://github.com/kusuridheeraj/Aegis)**

*Next week: I’ll be building the Python FastAPI AI brain that consumes this Kafka stream to generate real-time vector embeddings.*

#SystemDesign #Architecture #SpringBoot #Kafka #DataEngineering #StaffEngineer
