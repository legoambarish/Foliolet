package com.sih26190.dms.model;

import java.time.LocalDateTime;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * A hash reported by the local watcher script the moment a file
 * appeared or changed in the watched intake folder, before any upload
 * happened. Kept separate from DocumentRecord entirely, this table
 * exists purely so upload() has something independent to compare
 * against: an earliest-known-state fingerprint the uploader never had
 * a chance to influence after the fact.
 */
@Entity
@Table(name = "candidate_hashes")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class CandidateHash {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long ownerId;

    private String filename;

    private String sha256Hash;

    private LocalDateTime capturedAt;

}