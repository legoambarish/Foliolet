package com.sih26190.dms.selective.repository;

import com.sih26190.dms.selective.model.CredentialDocument;
import jakarta.persistence.LockModeType;
import java.util.*;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;

public interface CredentialDocumentRepository extends JpaRepository<CredentialDocument, String> {
  List<CredentialDocument> findByOwnerIdOrderByCreatedAtDesc(Long ownerId);

  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select d from CredentialDocument d where d.id = :id")
  Optional<CredentialDocument> locked(@Param("id") String id);
}
