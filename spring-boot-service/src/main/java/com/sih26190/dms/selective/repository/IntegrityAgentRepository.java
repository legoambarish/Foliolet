package com.sih26190.dms.selective.repository;

import com.sih26190.dms.selective.model.IntegrityAgent;
import jakarta.persistence.LockModeType;
import java.util.*;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;

public interface IntegrityAgentRepository extends JpaRepository<IntegrityAgent, String> {
  List<IntegrityAgent> findByOwnerIdOrderByCreatedAtDesc(Long ownerId);

  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select a from IntegrityAgent a where a.id = :id")
  Optional<IntegrityAgent> locked(@Param("id") String id);
}
