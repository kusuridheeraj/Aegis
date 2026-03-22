# Testing Project Aegis: Week 1 Execution Guide

This guide provides step-by-step instructions to test the Enterprise Ingestion Gateway you built in Week 1. This proves that your Spring Boot application successfully streams large files to MinIO and publishes events to Apache Kafka without crashing the JVM.

## Prerequisites
Ensure Docker Desktop is running and your infrastructure is up:
```bash
docker-compose ps
# You should see 'aegis-kafka' and 'aegis-minio' running.
```

---

## Step 1: Start the Spring Boot Gateway

You need to spin up the Java API that will receive the document uploads.

1. Open a new terminal.
2. Navigate to the gateway directory:
   ```bash
   cd aegis-ingestion-gateway
   ```
3. Run the Spring Boot application:
   ```bash
   .\mvnw.cmd spring-boot:run
   ```
4. Wait until you see a log line that looks like: `Started AegisIngestionGatewayApplication in X.XXX seconds`.

---

## Step 2: Generate Massive Test Files

To truly test the "Claim Check" pattern, a tiny text file isn't enough. We need to hit the server with 500MB and 1GB files to prove that the JVM memory doesn't spike. 

We have provided a PowerShell script to instantly generate these files.

1. Open a new terminal in the root of the project.
2. Run the script:
   ```powershell
   .\scripts\generate_test_files.ps1
   ```
This will instantly create `temp_500mb.bin` and `temp_1gb.bin` in your project root.

---

## Step 3: Fire the Payload at the Gateway

Now, let's upload the 1GB file to the running Spring Boot server.

1. In your terminal, run this `curl` command (using `curl.exe` on Windows):
   ```bash
   curl.exe -X POST -F "file=@temp_1gb.bin" http://localhost:8080/api/v1/documents
   ```

### What you should see:
You will instantly get a response like this (usually in around 12-20 milliseconds):
```json
{"status":"accepted","objectId":"some-uuid-temp_1gb.bin","message":"Document ingestion started successfully."}
```
*Look at your Spring Boot terminal logs.* You will see logs confirming the file was streamed to MinIO and an event was published to Kafka!

---

## Step 4: Verify the "Claim Check" in MinIO

Let's verify the 1GB file actually made it to the object storage.

1. Open your web browser and go to: [http://localhost:9001](http://localhost:9001)
2. Log in with:
   * **Username:** `aegis_admin`
   * **Password:** `aegis_password`
3. Click on the **Object Browser** on the left menu, then the `aegis-raw-docs` bucket.
4. You should see your massive `temp_1gb.bin` file sitting there securely.

---

## Step 5: Clean Up

Because we are dealing with massive files, you will want to clean up your local disk and your MinIO storage after testing.

### 1. Delete Local Test Files
Run the generation script with the `-Clean` flag to delete the `temp_500mb.bin` and `temp_1gb.bin` files:
```powershell
.\scripts\generate_test_files.ps1 -Clean
```

### 2. Clear the MinIO Bucket
If you uploaded multiple 1GB files during testing, your Docker volume will fill up quickly. Run this command to forcefully delete everything inside the `aegis-raw-docs` MinIO bucket:

```bash
docker run --rm --network aegis_default --entrypoint sh minio/mc -c "mc alias set myminio http://aegis-minio:9000 aegis_admin aegis_password && mc rm -r --force myminio/aegis-raw-docs/"
```
*Note: This connects directly to the Docker network, authenticates with your MinIO container, and recursively removes all contents in the bucket.*
