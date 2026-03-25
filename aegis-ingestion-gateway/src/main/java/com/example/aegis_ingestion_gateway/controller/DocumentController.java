package com.example.aegis_ingestion_gateway.controller;

import com.example.aegis_ingestion_gateway.model.DocumentIngestedEvent;
import com.example.aegis_ingestion_gateway.service.KafkaProducerService;
import com.example.aegis_ingestion_gateway.service.MinioService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

@Slf4j
@RestController
@RequestMapping("/api/v1/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final MinioService minioService;
    private final KafkaProducerService kafkaProducerService;

    @GetMapping("/health")
    public ResponseEntity<String> healthCheck() {
        return ResponseEntity.ok("Gateway is healthy");
    }

    @PostMapping
    public ResponseEntity<?> uploadDocument(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return ResponseEntity.badRequest().body("File is empty");
        }

        // Generate the distributed Correlation ID right at the gateway edge
        String correlationId = UUID.randomUUID().toString();
        log.info("[{}] Received upload request for file: {}", correlationId, file.getOriginalFilename());

        try {
            // 1. Claim Check: Save massive file to object store immediately
            String objectId = minioService.uploadFile(file);
            log.info("[{}] Successfully uploaded to MinIO. ObjectId: {}", correlationId, objectId);

            // 2. Publish lightweight event to Kafka
            DocumentIngestedEvent event = DocumentIngestedEvent.builder()
                    .correlationId(correlationId)
                    .objectId(objectId)
                    .originalFilename(file.getOriginalFilename())
                    .contentType(file.getContentType())
                    .sizeBytes(file.getSize())
                    .ingestedAt(Instant.now())
                    .build();
                    
            kafkaProducerService.sendEvent(event);
            log.info("[{}] Published event to Kafka", correlationId);

            // 3. Return 202 Accepted to free up the client immediately
            return ResponseEntity.status(HttpStatus.ACCEPTED)
                    .body(Map.of(
                        "status", "accepted", 
                        "objectId", objectId, 
                        "correlationId", correlationId,
                        "message", "Document ingestion started successfully."
                    ));
                    
        } catch (Exception e) {
            log.error("[{}] Ingestion failed", correlationId, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("Failed to process document: " + e.getMessage());
        }
    }
}