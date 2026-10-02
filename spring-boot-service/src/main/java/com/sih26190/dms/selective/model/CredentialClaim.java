package com.sih26190.dms.selective.model;

import jakarta.persistence.*;

@Entity
@Table(name = "wallet_claims")
public class CredentialClaim {
  @Id public String id;

  @Column(nullable = false)
  public String credentialId;

  public int leafIndex;
  public String path;
  public String label;
  public String type;
  public String derivedFrom;

  @Column(columnDefinition = "TEXT", nullable = false)
  public String encryptedLeaf;

  public String leafHash;
}
