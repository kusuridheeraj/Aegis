package com.example.aegis_ingestion_gateway.service;

import io.minio.PutObjectArgs;
import io.minio.MinioClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class MinioService {
    private final MinioClient minioClient;

    @Value("${minio.bucket-name}")
    private String bucketName;

    public String uploadFile(MultipartFile file) throws Exception {
        String objectId = UUID.randomUUID().toString() + "-" + file.getOriginalFilename();
        
        try (InputStream inputStream = file.getInputStream()) {
            minioClient.putObject(
                PutObjectArgs.builder()
                    .bucket(bucketName)
                    .object(objectId)
                    .stream(file.getInputStream(), file.getSize(), -1)
                    .contentType(file.getContentType() != null ? file.getContentType() : "application/octet-stream")
                    .build());
        }
        
        log.info("Successfully uploaded file {} to MinIO as {}", file.getOriginalFilename(), objectId);
        return objectId;
    }

    public boolean checkHealth() {
        try {
            return minioClient.bucketExists(
                io.minio.BucketExistsArgs.builder().bucket(bucketName).build());
        } catch (Exception e) {
            log.error("MinIO Health Check Failed: {}", e.getMessage());
            return false;
        }
    }
}
