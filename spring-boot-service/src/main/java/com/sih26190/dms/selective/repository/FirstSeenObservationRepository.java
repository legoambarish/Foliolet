package com.sih26190.dms.selective.repository;

import com.sih26190.dms.selective.model.FirstSeenObservation;
import java.util.*;
import org.springframework.data.jpa.repository.*;

public interface FirstSeenObservationRepository
    extends JpaRepository<FirstSeenObservation, String> {
  List<FirstSeenObservation> findByAgentIdAndItemIdOrderBySequenceAsc(
      String agentId, String itemId);

  List<FirstSeenObservation> findByOwnerIdOrderByReceivedAtDesc(Long ownerId);

  Optional<FirstSeenObservation> findByAgentIdAndSequence(String agentId, long sequence);
  Optional<FirstSeenObservation> findFirstByAgentIdAndSha256AndFilenameOrderByReceivedAtDesc(String agentId,String sha256,String filename);
}
