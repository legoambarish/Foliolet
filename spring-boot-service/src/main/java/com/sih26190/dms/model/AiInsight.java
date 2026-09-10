package com.sih26190.dms.model;

import java.time.LocalDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "ai_insights")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class AiInsight {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long documentId;

    private String requestedBy;


    private String status;

    @Column(columnDefinition = "TEXT")
    private String resultJson;

    private LocalDateTime createdAt;

}