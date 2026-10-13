package com.sih26190.dms.bridge;

import com.sih26190.dms.repository.UserRepository;
import java.security.Principal;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/bridge/imports")
@ConditionalOnProperty(name = "bridge.enabled", havingValue = "true")
public class ImportController {
  private final ImportService imports;
  private final UserRepository users;

  public ImportController(ImportService imports, UserRepository users) {
    this.imports = imports;
    this.users = users;
  }

  private com.sih26190.dms.model.User user(Principal p) {
    return users.findByUsername(p.getName()).orElseThrow();
  }

  @PostMapping("/start")
  public Map<String, Object> start(Principal p, @RequestBody Map<String, Object> b)
      throws Exception {
    return imports.start(user(p), b);
  }

  @GetMapping("/{id}")
  public Map<String, Object> status(Principal p, @PathVariable String id) {
    return imports.status(user(p), id);
  }

  @PostMapping("/{id}/consent")
  public Map<String, Object> consent(
      Principal p, @PathVariable String id, @RequestBody Map<String, Object> b) throws Exception {
    return imports.consent(user(p), id, b);
  }

  @PostMapping("/{id}/fetch")
  public Map<String, Object> fetch(
      Principal p, @PathVariable String id, @RequestBody Map<String, Object> b) throws Exception {
    return imports.fetch(user(p), id, b);
  }

  @PostMapping("/xml")
  public Map<String, Object> xml(Principal p, @RequestBody Map<String, Object> b) throws Exception {
    return imports.xml(user(p), b);
  }

  @PostMapping("/{id}/cancel")
  public Map<String, Object> cancel(Principal p, @PathVariable String id) {
    return imports.cancel(user(p), id);
  }

  @PostMapping("/{id}/confirm")
  public Map<String, Object> confirm(Principal p, @PathVariable String id) {
    return imports.confirm(user(p), id);
  }

  @ExceptionHandler(SecurityException.class)
  public ResponseEntity<?> forbidden(Exception e) {
    return ResponseEntity.status(403).body(Map.of("message", e.getMessage()));
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<?> invalid(Exception e) {
    return ResponseEntity.badRequest()
        .body(
            Map.of(
                "message",
                e instanceof IllegalArgumentException
                    ? e.getMessage()
                    : "Import unavailable or invalid XML"));
  }
}
