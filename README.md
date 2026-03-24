# Project Aegis

**A Distributed Enterprise RAG Engine & Real-Time Context System**

This project demonstrates an event-driven architecture bridging a Java JVM ingestion backend with a Python ML service, designed for high availability, low latency, and heavy data workloads using the Claim Check pattern.

## Architecture Diagram
```mermaid
graph TD;
    Client((Client)) -->|Upload Document| SpringBoot[Spring Boot Gateway];
    SpringBoot -->|1. Stream File Bytes| MinIO[(MinIO Object Store)];
    MinIO -.->|2. Returns objectId| SpringBoot;
    SpringBoot -->|3. Publish DocumentIngestedEvent| Kafka[[Apache Kafka Event Bus]];
    SpringBoot -.->|4. HTTP 202 Accepted| Client;
    Kafka -->|5. Consume Event| FastAPI[FastAPI AI Service];
    FastAPI -->|6. Fetch File via objectId| MinIO;
    FastAPI -->|7. Generate Vector Embeddings| LLM((HuggingFace LLM));
    LLM -.->|8. Return Embeddings| FastAPI;
    FastAPI -->|9. Store Vectors| VectorDB[(Qdrant Vector DB)];
    MCPServer[MCP Interface] -->|Query Context| FastAPI;
    AIAgent((LangGraph / Claude)) -->|Native Query Protocol| MCPServer;

    classDef java fill:#b07219,stroke:#333,stroke-width:2px,color:#fff;
    classDef python fill:#3572A5,stroke:#333,stroke-width:2px,color:#fff;
    classDef storage fill:#154c79,stroke:#333,stroke-width:2px,color:#fff;
    classDef queue fill:#e35d25,stroke:#333,stroke-width:2px,color:#fff;
    
    class SpringBoot java;
    class FastAPI python;
    class MinIO,VectorDB storage;
    class Kafka queue;
```

## Technologies
* **Ingestion Gateway:** Java 21, Spring Boot 3, Spring Kafka
* **Message Broker:** Apache Kafka (KRaft mode)
* **Object Storage:** MinIO (S3 compatible)
* **AI Service:** Python 3.11, FastAPI, HuggingFace, LangChain, LangGraph
* **Vector DB:** Qdrant
* **Deployment:** Docker Compose (Isolated bridge network)

## 📚 Documentation & Deep Dives

To keep this README concise, all detailed system mechanics, testing guides, and engineering trade-offs have been modularized. Please explore the links below:

* 🏛️ **[Architecture Decision Records (ADR)](ARCHITECTURE.md)** 
  * *Read this to understand the "Why".* Covers the trade-offs of I/O vs CPU decoupling, why we used LangChain over naive chunking, Qdrant over PostgreSQL, and our DLQ/Tracing fault-tolerance strategy.
* 🧪 **[Testing & Ingestion Guide](docs/Ingestion_Testing_Guide.md)** 
  * *Read this to run the code.* Step-by-step instructions for spinning up the Docker cluster and using the batch scripts (`.ps1` and `.sh`) to ingest your own PDF books or codebase into the vector engine.
* 📝 **[Engineering Blog Series](blogs/)** 
  * *Read this for production war stories.* Deep dives into how we dropped API latency from 32s to 12ms, and how we solved a 62MB JSON payload bug caused by binary escaping.

## Quick Start (Local Cluster)

1. Spin up the infrastructure (Kafka, MinIO, Qdrant):
   ```bash
   docker-compose up -d
   ```
2. Follow the **[Testing Guide](docs/Ingestion_Testing_Guide.md)** to start the Java and Python microservices and batch-upload your documents.