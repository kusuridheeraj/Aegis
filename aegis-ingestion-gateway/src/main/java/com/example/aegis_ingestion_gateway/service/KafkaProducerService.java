package com.example.aegis_ingestion_gateway.service;

import com.example.aegis_ingestion_gateway.model.DocumentIngestedEvent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class KafkaProducerService {
    private final KafkaTemplate<String, Object> kafkaTemplate;
    private static final String TOPIC = "aegis.documents.raw";

    public void sendEvent(DocumentIngestedEvent event) {
        kafkaTemplate.send(TOPIC, event.getObjectId(), event);
        log.info("Published ingestion event to Kafka topic {} for objectId {}", TOPIC, event.getObjectId());
    }
}
