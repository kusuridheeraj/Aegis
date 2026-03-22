package com.example.aegis_ingestion_gateway.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

@Configuration
public class KafkaTopicConfig {
    @Bean
    public NewTopic rawDocsTopic() {
        return TopicBuilder.name("aegis.documents.raw")
                .partitions(3)
                .replicas(1)
                .build();
    }
}
