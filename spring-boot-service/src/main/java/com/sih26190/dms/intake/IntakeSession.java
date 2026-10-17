package com.sih26190.dms.intake;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name="wallet_intake_sessions")
public class IntakeSession {
  @Id public String id;
  public Long ownerId;
  public String agentId;
  public String tokenHash;
  public String folderHash;
  @Column(columnDefinition="TEXT") public String encryptedFolder;
  public Instant createdAt;
  public Instant expiresAt;
  public Instant lastSeen;
  public boolean revoked;
  public int imported;
  @Version public long lockVersion;
}
