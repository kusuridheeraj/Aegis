package com.example.aegis_ingestion_gateway.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DocumentIngestedEvent {
    private String objectId;
    private String originalFilename;
    private String contentType;
    private long sizeBytes;
    private Instant ingestedAt;
}
