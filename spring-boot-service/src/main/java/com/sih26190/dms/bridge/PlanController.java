package com.sih26190.dms.bridge;

import com.sih26190.dms.repository.UserRepository;
import java.security.Principal;
import java.util.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/bridge/plans")
@ConditionalOnProperty(name = "bridge.enabled", havingValue = "true")
public class PlanController {
  private final PlanService plans;
  private final UserRepository users;

  public PlanController(PlanService plans, UserRepository users) {
    this.plans = plans;
    this.users = users;
  }

  private com.sih26190.dms.model.User user(Principal p) {
    return users.findByUsername(p.getName()).orElseThrow();
  }

  @PostMapping
  public Object propose(Principal p, @RequestBody Map<String, Object> input) {
    return plans.propose(user(p), input);
  }

  @GetMapping("/{id}")
  public Object status(Principal p, @PathVariable String id) {
    return plans.status(user(p), id);
  }

  @PostMapping("/{id}/approve")
  public Object approve(
      Principal p, @PathVariable String id, @RequestBody Map<String, Object> input) {
    return plans.approve(user(p), id, input);
  }

  @PostMapping("/{id}/cancel")
  public Object cancel(Principal p, @PathVariable String id) {
    return plans.cancel(user(p), id);
  }

  @PostMapping("/{id}/execute")
  public Object execute(Principal p, @PathVariable String id) {
    return plans.execute(user(p), id);
  }

  @ExceptionHandler(SecurityException.class)
  public org.springframework.http.ResponseEntity<?> denied(SecurityException e) {
    return org.springframework.http.ResponseEntity.status(403)
        .body(Map.of("message", e.getMessage()));
  }

  @ExceptionHandler(IllegalArgumentException.class)
  public org.springframework.http.ResponseEntity<?> invalid(IllegalArgumentException e) {
    return org.springframework.http.ResponseEntity.badRequest()
        .body(Map.of("message", e.getMessage()));
  }
}
