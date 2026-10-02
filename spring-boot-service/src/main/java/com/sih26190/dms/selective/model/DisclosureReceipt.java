package com.sih26190.dms.selective.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "disclosure_receipts")
public class DisclosureReceipt {
  @Id public String id;
  public String grantId;
  public Instant verifiedAt;
  public String result;
}
