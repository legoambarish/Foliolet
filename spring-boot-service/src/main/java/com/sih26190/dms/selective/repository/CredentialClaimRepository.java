package com.sih26190.dms.selective.repository;

import com.sih26190.dms.selective.model.CredentialClaim;
import java.util.*;
import org.springframework.data.jpa.repository.*;

public interface CredentialClaimRepository extends JpaRepository<CredentialClaim, String> {
  List<CredentialClaim> findByCredentialIdOrderByLeafIndexAsc(String credentialId);

  void deleteByCredentialId(String credentialId);
}
