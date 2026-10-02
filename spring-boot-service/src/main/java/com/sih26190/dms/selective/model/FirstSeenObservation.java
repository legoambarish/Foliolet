package com.sih26190.dms.selective.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "first_seen_observations")
public class FirstSeenObservation {
  @Id public String id;
  public Long ownerId;
  public String agentId;
  public String itemId;
  public String filename;
  public String sha256;
  public String digest;
  public long sequence;
  public Instant receivedAt;
  public Instant observedAt;
}
