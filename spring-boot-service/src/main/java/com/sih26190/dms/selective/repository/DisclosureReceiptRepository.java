package com.sih26190.dms.selective.repository;

import com.sih26190.dms.selective.model.DisclosureReceipt;
import java.util.*;
import org.springframework.data.jpa.repository.*;

public interface DisclosureReceiptRepository extends JpaRepository<DisclosureReceipt, String> {
  List<DisclosureReceipt> findByGrantIdOrderByVerifiedAtDesc(String grantId);
}
