package com.sih26190.dms.intake;

import jakarta.persistence.*;
import java.time.Instant;

/** Context only; none of these fields enter v1 signed disclosure bundles. */
@Entity
@Table(name = "wallet_intake_records")
public class IntakeRecord {
  @Id public String credentialId;
  public Long ownerId;
  public String sourceHash;
  public String sourceVersion;
  public String method = "MANUAL_UPLOAD";
  public String sessionId;
  public String observationId;
  public String state = "QUEUED";
  public String stage = "Queued for local reading";
  public String indicator = "INCONCLUSIVE";
  public String lineage = "NOT_ASSESSED";
  public Instant updatedAt;
  public Instant startedAt;
  public Instant confirmedAt;
  public int attempts;
  @Column(columnDefinition = "TEXT") public String encryptedReport;
  @Column(columnDefinition = "TEXT") public String encryptedHistory;
  @Column(columnDefinition = "TEXT") public String encryptedBaseline;
  @Column(columnDefinition = "TEXT") public String encryptedChanges;
  @Version public long lockVersion;
}
