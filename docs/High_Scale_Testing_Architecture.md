# Scaling Project Aegis: 10 Million Hits/Second with 1GB Uploads

Your current Week 1 architecture successfully implements the Claim Check pattern to decouple heavy uploads from processing. However, if you are targeting Staff-level (SDE-3) engineering interviews at top-tier companies, you need to understand the physical and theoretical limits of your architecture.

What happens if you scale this to **10,000,000 requests per second**, where each request is a **1GB file**?

Let's break down the math, the inevitable bottlenecks, the testing strategy, and the architectural overhauls required to survive this apocalyptic load.

## The Reality Check (The Math)
Before writing code, Staff engineers do napkin math:
* **Payload:** 1GB per request.
* **Throughput:** 10,000,000 requests per second.
* **Bandwidth Required:** 10,000,000 GB/sec = **10 Petabytes per second**.

**Fact:** No single datacenter on Earth has a 10 Petabyte/sec ingress pipe. AWS's entire global backbone would likely struggle to absorb this simultaneously at a single regional endpoint. 

Therefore, testing this on a local machine or a single cloud region is physically impossible. You are now entering the realm of hyper-distributed, multi-region architecture.

---

## 1. How Does the Current Architecture Hold Up?

If you simulated even a fraction of this load against your current Spring Boot -> MinIO -> Kafka setup, here is exactly how it would die:

1.  **Network Saturation (Immediate Death):** Your server's Network Interface Card (NIC) would hit 100% capacity in milliseconds. The OS would start dropping TCP SYN packets. Clients would see "Connection Timeout".
2.  **Tomcat Thread Exhaustion:** Spring Boot (using standard Tomcat) allocates a thread per request. Even though streaming to MinIO doesn't use much RAM, you are holding a thread open for the duration of the 1GB transfer. You would exhaust your thread pool instantly.
3.  **Storage I/O Bottleneck:** Your local disk (where MinIO writes) has a maximum write speed (e.g., 5,000 MB/s for a fast NVMe SSD). Once that is saturated, MinIO pushes back on Spring Boot, causing the upload streams to slow down, holding the threads open longer, exacerbating bottleneck #2.
4.  **Kafka Partition Limits:** While the events are small, pushing 10 million messages/sec into a single-node Kafka cluster with 1 partition will overwhelm the broker's disk I/O and CPU.

---

## 2. What Needs to Change? (The Architectural Overhaul)

To handle this load, the architecture must fundamentally shift from a centralized gateway to a globally distributed edge network.

### A. The "Direct Upload" Pattern (Pre-signed URLs)
**The biggest change:** Spring Boot can no longer touch the 1GB file. The network bandwidth cost of routing 10 PB/sec through your application servers is astronomical.
*   **The Fix:** When the client wants to upload, they make a tiny HTTP request to Spring Boot: *"I want to upload a 1GB file."*
*   Spring Boot asks AWS S3 (or a distributed MinIO cluster) for a **Pre-Signed URL**.
*   Spring Boot returns the URL to the client.
*   The client uploads the 1GB file *directly* to the S3 bucket, completely bypassing your application servers.
*   S3 uses an "Object Created" event notification to drop a message into an SQS queue or Kafka topic, triggering your downstream Python ML workers.

### B. Reactive/Non-Blocking Web Stack (Spring WebFlux)
For the API calls that *do* hit the server (authentication, requesting pre-signed URLs), Tomcat's thread-per-request model is too heavy.
*   **The Fix:** Migrate from Spring Web MVC to **Spring WebFlux** (Project Reactor). This uses an Event Loop (like Node.js) and non-blocking I/O. It can handle hundreds of thousands of concurrent connections on a single machine using very few threads.

### C. Global Edge Routing (Anycast & CDN)
*   **The Fix:** Put the API behind Cloudflare or AWS CloudFront using Anycast routing. Users hit the Edge location closest to them, and the heavy 1GB files are routed over the cloud provider's optimized private backbone rather than the public internet.

### D. Partitioning the Message Broker
*   **The Fix:** Kafka needs to be scaled horizontally. 10M events/sec requires a massive Kafka cluster (e.g., 50+ brokers) with topics heavily partitioned (e.g., 1000+ partitions) so the write load is distributed across many physical disks.

---

## 3. How to Actually Test This (Load Testing Strategy)

You cannot generate 10M hits/sec from your laptop. Load testing at this scale requires a distributed botnet.

### Step 1: Distributed Load Generation
Tools like **Locust**, **Gatling**, or **k6** are designed for this. You deploy "worker" nodes across hundreds of EC2 instances in multiple AWS regions. A "master" node orchestrates them to attack your endpoint simultaneously.

### Step 2: The "Mock" Testing Approach
Because pushing 10 Petabytes/sec is impossible and prohibitively expensive, you test the *components* independently:

1.  **Test the Control Plane (Spring Boot):** Disable the actual file upload. Use Locust to blast the Spring Boot endpoint requesting Pre-signed URLs at 100k requests/sec. See how WebFlux and your CPU handle the connection volume.
2.  **Test the Data Plane (Storage):** Run AWS benchmarks directly against your storage cluster (S3/MinIO) to determine the maximum sustained write throughput of your disks/network.
3.  **Test the Event Bus (Kafka):** Use Kafka's built-in `kafka-producer-perf-test.sh` script to blast 10M tiny JSON events/sec into your cluster and measure latency and dropped messages.

### Summary for your Resume/Interview
If an interviewer asks, *"How does this scale?"* you reply:

> *"The current architecture uses the Claim Check pattern to protect the JVM memory, which is sufficient for high-volume enterprise traffic. However, if we scale to extreme payloads like 10 million concurrent 1GB uploads, I would immediately pivot to a Direct-to-S3 Pre-signed URL architecture. I would shift the Spring Boot gateway to WebFlux to handle the concurrent connection load without thread exhaustion, and I would horizontally partition the Kafka cluster to absorb the massive influx of 'Object Created' events triggered by the storage layer."*