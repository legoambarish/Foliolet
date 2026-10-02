package com.sih26190.dms.selective.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "wallet_documents")
public class CredentialDocument {
  @Id public String id;
  public String logicalId;
  public Long ownerId;
  public String displayName;
  public String category;
  public String originalFilename;
  public String filePath;
  public String backupPath;
  public String documentHash;
  public String documentSalt;
  public String documentCommitment;
  public String merkleRoot;
  public String provenanceLevel;

  @Column(columnDefinition = "TEXT")
  public String provenanceJson;

  public String provenanceDigest;
  public String status;
  public int version;
  public String previousId;
  public String supersededBy;
  public String anchorTx;
  public String contractAddress;
  public long chainId;
  public Instant createdAt;
  public Instant anchoredAt;
  @Version public long lockVersion;
}
