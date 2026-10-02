package com.sih26190.dms.selective.repository;

import com.sih26190.dms.selective.model.DisclosureGrant;
import jakarta.persistence.LockModeType;
import java.util.*;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;

public interface DisclosureGrantRepository extends JpaRepository<DisclosureGrant, String> {
  List<DisclosureGrant> findByOwnerIdOrderByCreatedAtDesc(Long ownerId);

  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select g from DisclosureGrant g where g.tokenHash = :hash")
  Optional<DisclosureGrant> byTokenLocked(@Param("hash") String hash);

  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select g from DisclosureGrant g where g.id = :id")
  Optional<DisclosureGrant> locked(@Param("id") String id);
}
