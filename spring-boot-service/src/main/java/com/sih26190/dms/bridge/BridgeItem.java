package com.sih26190.dms.bridge;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "bridge_items")
@Getter
@Setter
@NoArgsConstructor
public class BridgeItem {
  @Id private String id;

  @Column(nullable = false)
  private String kind;

  @Column(nullable = false)
  private String owner;

  private String recipient;

  @Column(nullable = false)
  private String status;

  @Column(columnDefinition = "text", nullable = false)
  private String encryptedPayload;

  private long createdAt;
  private long expiresAt;
  private int opens;
  private String referenceId;
  @Version private long revision;
}
