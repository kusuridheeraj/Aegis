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

@Slf4j
@RestController
@RequestMapping("/api/v1/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final MinioService minioService;
    private final KafkaProducerService kafkaProducerService;

    @PostMapping
    public ResponseEntity<?> uploadDocument(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return ResponseEntity.badRequest().body("File is empty");
        }

        try {
            // 1. Claim Check: Save massive file to object store immediately
            String objectId = minioService.uploadFile(file);

            // 2. Publish lightweight event to Kafka
            DocumentIngestedEvent event = DocumentIngestedEvent.builder()
                    .objectId(objectId)
                    .originalFilename(file.getOriginalFilename())
                    .contentType(file.getContentType())
                    .sizeBytes(file.getSize())
                    .ingestedAt(Instant.now())
                    .build();
                    
            kafkaProducerService.sendEvent(event);

            // 3. Return 202 Accepted to free up the client immediately
            return ResponseEntity.status(HttpStatus.ACCEPTED)
                    .body(Map.of("status", "accepted", "objectId", objectId, "message", "Document ingestion started successfully."));
                    
        } catch (Exception e) {
            log.error("Ingestion failed", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("Failed to process document: " + e.getMessage());
        }
    }
}
