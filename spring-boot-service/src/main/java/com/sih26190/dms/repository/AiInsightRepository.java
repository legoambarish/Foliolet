package com.sih26190.dms.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.sih26190.dms.model.AiInsight;

public interface AiInsightRepository extends JpaRepository<AiInsight, Long> {

    Optional<AiInsight> findFirstByDocumentIdOrderByCreatedAtDesc(Long documentId);

}