package com.sih26190.dms.selective;

import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.*;
import com.sih26190.dms.selective.WalletDtos.*;
import jakarta.validation.Valid;
import java.util.*;
import org.springframework.http.*;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/wallet")
public class WalletController {
  private final WalletService wallet;
  private final DisclosureService disclosures;
  private final IntegrityService integrity;
  private final UserRepository users;
  private final AuditLogRepository audit;

  public WalletController(
      WalletService wallet,
      DisclosureService disclosures,
      IntegrityService integrity,
      UserRepository users,
      AuditLogRepository audit) {
    this.wallet = wallet;
    this.disclosures = disclosures;
    this.integrity = integrity;
    this.users = users;
    this.audit = audit;
  }

  private User user(Authentication auth) {
    return users.findByUsername(auth.getName()).orElseThrow();
  }

  @GetMapping("/documents")
  public Object list(Authentication auth) {
    return wallet.list(user(auth));
  }

  @PostMapping("/documents")
  public Object enroll(
      @RequestParam MultipartFile file,
      @RequestParam String displayName,
      @RequestParam String category,
      @RequestParam(required = false) String observationId,
      Authentication auth) {
    return wallet.enroll(file, displayName, category, observationId, null, user(auth));
  }

  @PostMapping("/documents/{id}/versions")
  public Object version(
      @PathVariable String id,
      @RequestParam MultipartFile file,
      @RequestParam String displayName,
      @RequestParam String category,
      @RequestParam(required = false) String observationId,
      Authentication auth) {
    return wallet.enroll(file, displayName, category, observationId, id, user(auth));
  }

  @GetMapping("/documents/{id}")
  public Object detail(@PathVariable String id, Authentication auth) {
    return wallet.detail(id, user(auth));
  }

  @PutMapping("/documents/{id}/claims")
  public Object claims(
      @PathVariable String id, @Valid @RequestBody ConfirmClaims input, Authentication auth) {
    return wallet.confirm(id, input, user(auth));
  }

  @PostMapping("/documents/{id}/anchor")
  public Object anchor(@PathVariable String id, Authentication auth) {
    return wallet.anchor(id, user(auth));
  }

  @PostMapping("/documents/{id}/revoke")
  public Object revoke(@PathVariable String id, Authentication auth) {
    wallet.revoke(id, user(auth));
    return Map.of("status", "REVOKED");
  }

  @PostMapping("/documents/{id}/integrity")
  public Object verify(
      @PathVariable String id,
      @RequestParam(defaultValue = "false") boolean restore,
      Authentication auth) {
    return wallet.verifyFile(id, user(auth), restore);
  }

  @GetMapping("/documents/{id}/file")
  public ResponseEntity<byte[]> file(@PathVariable String id, Authentication auth) {
    var result = wallet.download(id, user(auth));
    return ResponseEntity.ok()
        .cacheControl(CacheControl.noStore())
        .header(
            HttpHeaders.CONTENT_DISPOSITION,
            ContentDisposition.attachment()
                .filename((String) result.get("filename"), java.nio.charset.StandardCharsets.UTF_8)
                .build()
                .toString())
        .contentType(MediaType.APPLICATION_OCTET_STREAM)
        .body((byte[]) result.get("bytes"));
  }

  @PostMapping("/disclosures")
  public Object disclose(@Valid @RequestBody ShareRequest request, Authentication auth) {
    return disclosures.create(request, user(auth));
  }

  @GetMapping("/disclosures")
  public Object grants(Authentication auth) {
    return disclosures.list(user(auth));
  }

  @PostMapping("/disclosures/{id}/revoke")
  public Object revokeGrant(@PathVariable String id, Authentication auth) {
    disclosures.revoke(id, user(auth));
    return Map.of("status", "REVOKED");
  }

  @GetMapping("/integrity/agents")
  public Object agents(Authentication auth) {
    return integrity.list(user(auth));
  }

  @PostMapping("/integrity/agents")
  public Object createAgent(@RequestBody Map<String, String> input, Authentication auth) {
    return integrity.create(user(auth), input.get("label"));
  }

  @PostMapping("/integrity/agents/{id}/revoke")
  public Object revokeAgent(@PathVariable String id, Authentication auth) {
    integrity.revoke(user(auth), id);
    return Map.of("active", false);
  }

  @GetMapping("/integrity/observations")
  public Object observations(Authentication auth) {
    return integrity.observations(user(auth));
  }

  @GetMapping("/activity")
  public Object activity(Authentication auth) {
    return audit.findByUserOrderByTimestampDesc(user(auth)).stream()
        .filter(e -> e.getCaseId() == null)
        .limit(200)
        .map(
            e -> {
              var row = new LinkedHashMap<String, Object>();
              row.put("action", e.getAction());
              row.put("timestamp", e.getTimestamp());
              row.put("credentialId", e.getCredentialId());
              row.put("disclosureId", e.getDisclosureId());
              return row;
            })
        .toList();
  }
}
