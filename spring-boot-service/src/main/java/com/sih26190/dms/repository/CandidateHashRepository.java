package com.sih26190.dms.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.sih26190.dms.model.CandidateHash;

public interface CandidateHashRepository extends JpaRepository<CandidateHash, Long> {

    Optional<CandidateHash> findFirstByFilenameAndOwnerIdOrderByCapturedAtAsc(String filename, Long ownerId);

    // Earliest record wins, that is the closest thing we have to
    // "what this file looked like the moment it first existed locally"
    Optional<CandidateHash> findFirstByFilenameOrderByCapturedAtAsc(String filename);

}