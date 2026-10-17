package com.sih26190.dms.intake;
import java.util.*;
import org.springframework.data.jpa.repository.JpaRepository;
public interface IntakeReceiptRepository extends JpaRepository<IntakeReceipt,String> {
  List<IntakeReceipt> findBySessionId(String sessionId);
}
