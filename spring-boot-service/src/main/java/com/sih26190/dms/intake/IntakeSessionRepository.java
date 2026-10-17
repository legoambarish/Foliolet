package com.sih26190.dms.intake;

import jakarta.persistence.LockModeType;
import java.util.*;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;

public interface IntakeSessionRepository extends JpaRepository<IntakeSession,String> {
  List<IntakeSession> findByRevokedFalseAndExpiresAtBefore(java.time.Instant before);
  List<IntakeSession> findByOwnerIdOrderByCreatedAtDesc(Long ownerId);
  Optional<IntakeSession> findByTokenHash(String tokenHash);
  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select s from IntakeSession s where s.id=:id")
  Optional<IntakeSession> locked(@Param("id") String id);
}
