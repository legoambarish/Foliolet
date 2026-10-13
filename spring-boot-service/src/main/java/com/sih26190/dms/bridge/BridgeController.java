package com.sih26190.dms.bridge;

import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;
import java.security.Principal;
import java.util.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

@RestController
@ConditionalOnProperty(name = "bridge.enabled", havingValue = "true")
public class BridgeController {
  private final BridgeService service;
  private final UserRepository users;

  public BridgeController(BridgeService service, UserRepository users) {
    this.service = service;
    this.users = users;
  }

  private User user(Principal p) {
    return users.findByUsername(p.getName()).orElseThrow();
  }

  @GetMapping("/api/bridge/state")
  public Object state(Principal p) {
    return service.state(user(p));
  }

  @GetMapping("/api/bridge/demo/live-grants")
  public Object live(Principal p) {
    return service.liveGrants(user(p));
  }

  @PostMapping("/api/bridge/demo/rogue-scenario")
  public Object rogue(Principal p) throws Exception {
    return service.rogueScenario(user(p));
  }

  @PostMapping("/api/bridge/holder-key")
  public Object bind(Principal p, @RequestBody Map<String, Object> body) {
    return service.bind(user(p), body);
  }

  @PostMapping("/api/bridge/issue")
  public Object issue(Principal p, @RequestBody Map<String, Object> body) throws Exception {
    return service.issue(user(p), body);
  }

  @PostMapping("/api/bridge/governance")
  public Object governance(Principal p, @RequestBody Map<String, Object> body) throws Exception {
    return service.governance(user(p), body);
  }

  @PostMapping("/api/bridge/credentials/{id}/retry")
  public Object retry(Principal p, @PathVariable String id) throws Exception {
    return service.retryIssue(user(p), id);
  }

  @PostMapping("/api/bridge/credentials/{id}/revoke")
  public Object revoke(Principal p, @PathVariable String id) throws Exception {
    service.revoke(user(p), id);
    return Map.of("status", "REVOKED");
  }

  @PostMapping("/api/bridge/requests")
  public Object request(Principal p, @RequestBody Map<String, Object> body) {
    return service.request(user(p), body);
  }

  @PostMapping("/api/bridge/draft")
  public Object draft(Principal p, @RequestBody Map<String, Object> body) {
    return service.draft(
        user(p), BridgeService.text(body, "requestId"), BridgeService.text(body, "credentialId"));
  }

  @PostMapping("/api/bridge/grants")
  public Object grant(Principal p, @RequestBody Map<String, Object> body) throws Exception {
    return service.grant(user(p), body);
  }

  @PostMapping("/api/bridge/grants/{id}/revoke")
  public Object revokeGrant(Principal p, @PathVariable String id) {
    service.revokeGrant(user(p), id);
    return Map.of("status", "REVOKED");
  }

  @PostMapping("/api/bridge/decisions")
  public Object decide(Principal p, @RequestBody Map<String, Object> body) throws Exception {
    return service.decide(user(p), body);
  }

  @PostMapping("/api/public/bridge/shares/{token}/open")
  public Object open(@PathVariable String token) {
    return service.open(token);
  }

  @GetMapping("/api/public/bridge/shares/{token}/status")
  public Object status(@PathVariable String token) {
    return service.grantStatus(token);
  }

  @ExceptionHandler(SecurityException.class)
  public ResponseEntity<?> denied(SecurityException e) {
    return ResponseEntity.status(403).body(Map.of("message", e.getMessage()));
  }

  @ExceptionHandler(org.springframework.web.server.ResponseStatusException.class)
  public ResponseEntity<?> statusError(org.springframework.web.server.ResponseStatusException e) {
    return ResponseEntity.status(e.getStatusCode())
        .body(Map.of("message", e.getReason() == null ? "Request refused" : e.getReason()));
  }

  @ExceptionHandler(IllegalArgumentException.class)
  public ResponseEntity<?> invalid(IllegalArgumentException e) {
    return ResponseEntity.badRequest().body(Map.of("message", e.getMessage()));
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<?> unavailable(Exception e) {
    return ResponseEntity.status(503)
        .body(Map.of("message", "Evidence service unavailable; no verification completed"));
  }
}
