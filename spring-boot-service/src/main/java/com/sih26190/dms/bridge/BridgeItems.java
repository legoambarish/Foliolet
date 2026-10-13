package com.sih26190.dms.bridge;

import jakarta.persistence.LockModeType;
import java.util.*;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;

public interface BridgeItems extends JpaRepository<BridgeItem, String> {
  List<BridgeItem> findByKindAndOwnerOrderByCreatedAtDesc(String kind, String owner);

  List<BridgeItem> findByKindAndRecipientOrderByCreatedAtDesc(String kind, String recipient);

  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select b from BridgeItem b where b.id=:id")
  Optional<BridgeItem> lock(@Param("id") String id);
}
