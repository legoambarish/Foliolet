package com.sih26190.dms.intake;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name="wallet_intake_receipts")
public class IntakeReceipt {
  @Id public String id;
  public String sessionId;
  public String sha256;
  public String credentialId;
  public Instant importedAt;
}
