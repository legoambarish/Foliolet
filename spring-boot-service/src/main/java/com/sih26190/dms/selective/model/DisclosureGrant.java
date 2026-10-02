package com.sih26190.dms.selective.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "disclosure_grants")
public class DisclosureGrant {
  @Id public String id;
  public Long ownerId;
  public String credentialId;

  @Column(unique = true, nullable = false, length = 64)
  public String tokenHash;

  public String verifierLabel;
  public String purpose;
  public String nonce;
  public Instant createdAt;
  public Instant expiresAt;
  public Instant revokedAt;
  public boolean oneTime;
  public int views;

  @Column(columnDefinition = "TEXT")
  public String selectedIds;

  @Column(columnDefinition = "TEXT")
  public String signedBundle;

  @Version public long lockVersion;
}
