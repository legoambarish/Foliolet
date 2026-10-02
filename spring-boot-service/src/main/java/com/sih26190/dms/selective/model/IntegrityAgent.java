package com.sih26190.dms.selective.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "integrity_agents")
public class IntegrityAgent {
  @Id public String id;
  public Long ownerId;
  public String label;

  @Column(columnDefinition = "TEXT")
  public String encryptedSecret;

  public boolean active = true;
  public long sequence;
  public String lastDigest;
  public Instant createdAt;
  @Version public long lockVersion;
}
