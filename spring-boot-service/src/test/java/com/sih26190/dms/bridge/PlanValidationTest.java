package com.sih26190.dms.bridge;

import static org.junit.jupiter.api.Assertions.*;

import java.util.*;
import org.junit.jupiter.api.Test;

class PlanValidationTest {
  private Map<String, Object> expected() {
    return Map.of(
        "credentialId",
        "doc",
        "requestId",
        "request",
        "claims",
        List.of("education.enrolled"),
        "purpose",
        "Internship",
        "verifier",
        "verifier",
        "expiresAt",
        123,
        "maxOpens",
        1,
        "steps",
        PlanService.STEPS);
  }

  @Test
  void modelCannotExpandScopeOrSteps() {
    var good = expected();
    assertDoesNotThrow(() -> PlanService.validateCandidate(good, good));
    for (String field :
        List.of("claims", "steps", "verifier", "purpose", "expiresAt", "maxOpens")) {
      var changed = new HashMap<>(good);
      changed.put(
          field,
          switch (field) {
            case "claims" -> List.of("bank.balance");
            case "steps" -> List.of("approve", "issue");
            case "expiresAt" -> 999999;
            case "maxOpens" -> 100;
            default -> "attacker";
          });
      assertThrows(
          IllegalArgumentException.class, () -> PlanService.validateCandidate(changed, good));
    }
  }

  @Test
  void hiddenExtraActionRejected() {
    var changed = new HashMap<>(expected());
    changed.put("tool", "revoke");
    assertThrows(
        IllegalArgumentException.class, () -> PlanService.validateCandidate(changed, expected()));
  }

  @Test
  void plannerAliasesCannotNominateOtherResourcesOrActions() {
    var safe =
        Map.<String, Object>of(
            "request",
            "selected-request",
            "credential",
            "selected-credential",
            "steps",
            PlanService.STEPS);
    assertDoesNotThrow(() -> AssistantService.validatePlanReferences(safe));
    for (String field : List.of("request", "credential", "steps", "tool")) {
      var evil = new HashMap<>(safe);
      evil.put(field, field.equals("steps") ? List.of("approve") : "attacker");
      assertThrows(
          IllegalArgumentException.class, () -> AssistantService.validatePlanReferences(evil));
    }
  }
}
