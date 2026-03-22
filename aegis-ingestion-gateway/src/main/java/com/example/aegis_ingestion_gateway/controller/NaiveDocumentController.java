package com.example.aegis_ingestion_gateway.controller;

import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.util.Map;
import java.util.UUID;

/**
 * NAIVE BASELINE ENDPOINT — Simulates a typical monolithic upload handler.
 *
 * This is intentionally BAD architecture used ONLY for benchmarking.
 * It reads the ENTIRE file into JVM heap memory (byte[]) before storing it.
 * With large files (500MB+), this will consume massive heap and may OOM.
 *
 * Compare this to the optimized DocumentController which uses the Claim Check Pattern.
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/documents/naive")
@RequiredArgsConstructor
public class NaiveDocumentController {

    private final MinioClient minioClient;

    @Value("${minio.bucket-name}")
    private String bucketName;

    @PostMapping
    public ResponseEntity<?> uploadDocumentNaive(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return ResponseEntity.badRequest().body("File is empty");
        }

        try {
            long startTime = System.currentTimeMillis();
            String objectId = "naive-" + UUID.randomUUID().toString() + "-" + file.getOriginalFilename();

            // ============================================================
            // THE ANTI-PATTERN: Buffer entire file into JVM heap memory
            // For a 1GB file, this allocates a 1GB byte[] on the heap!
            // ============================================================
            log.warn("NAIVE: Reading entire file into JVM heap memory: {} bytes", file.getSize());
            byte[] fileBytes = file.getBytes();  // ← THIS IS THE BOTTLENECK

            log.warn("NAIVE: File buffered in heap. Now uploading to MinIO synchronously...");

            // Upload from the in-memory byte array (not streaming)
            minioClient.putObject(
                PutObjectArgs.builder()
                    .bucket(bucketName)
                    .object(objectId)
                    .stream(new ByteArrayInputStream(fileBytes), fileBytes.length, -1)
                    .contentType(file.getContentType())
                    .build()
            );

            long duration = System.currentTimeMillis() - startTime;

            // No Kafka event — everything is synchronous and blocking
            log.info("NAIVE: Upload completed in {}ms for {} ({} bytes)", duration, file.getOriginalFilename(), file.getSize());

            return ResponseEntity.status(HttpStatus.OK)
                    .body(Map.of(
                        "status", "completed",
                        "objectId", objectId,
                        "approach", "naive-synchronous",
                        "processingTimeMs", duration,
                        "message", "Document uploaded synchronously (naive approach)."
                    ));

        } catch (OutOfMemoryError e) {
            log.error("NAIVE: JVM OUT OF MEMORY! File too large for heap: {}", file.getOriginalFilename(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of(
                        "status", "failed",
                        "error", "OutOfMemoryError",
                        "message", "JVM ran out of heap memory trying to buffer the file. This is exactly why the Claim Check Pattern exists."
                    ));
        } catch (Exception e) {
            log.error("NAIVE: Upload failed", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("Failed to process document: " + e.getMessage());
        }
    }
}
