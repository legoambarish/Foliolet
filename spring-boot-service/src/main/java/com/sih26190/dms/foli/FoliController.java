package com.sih26190.dms.foli;

import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;
import java.util.*;
import org.springframework.http.*;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/foli")
public class FoliController {
  private final UserRepository users;
  private final AuthorizedDocumentResolver resolver;
  private final FoliIndex index;
  private final FoliExtractionService extraction;
  private final FoliWorkGate gate;
  private final FoliJobs jobs;
  private final FoliLocalModel model;
  private final OcrService ocr;
  public FoliController(UserRepository users, AuthorizedDocumentResolver resolver, FoliIndex index,
      FoliExtractionService extraction, FoliWorkGate gate, FoliJobs jobs, FoliLocalModel model, OcrService ocr) {
    this.users=users; this.resolver=resolver; this.index=index; this.extraction=extraction; this.gate=gate;
    this.jobs=jobs; this.model=model; this.ocr=ocr;
  }
  User user(Authentication auth) { return users.findByUsername(auth.getName()).orElseThrow(AuthorizedDocumentResolver::missing); }
  @GetMapping("/documents") public List<FoliData.Document> documents(Authentication auth) { return resolver.list(user(auth)); }
  @GetMapping("/health") public Map<String,Object> health(Authentication auth) {
    user(auth); return Map.of("ollama",model.health(),"ocr",ocr.version(),"historyPersisted",false,"retentionSeconds",600);
  }
  @PostMapping("/jobs") public ResponseEntity<?> create(@jakarta.validation.Valid @RequestBody FoliJobs.Request request,Authentication auth) {
    return ResponseEntity.accepted().body(jobs.create(request,user(auth)));
  }
  @GetMapping("/jobs/{id}") public Map<String,Object> job(@PathVariable String id,Authentication auth) { return jobs.get(id,user(auth)); }
  @DeleteMapping("/jobs/{id}") public Map<String,Object> stop(@PathVariable String id,Authentication auth) { return jobs.stop(id,user(auth)); }
  @DeleteMapping("/memory") public Map<String,Object> forget(Authentication auth) { jobs.forget(user(auth)); return Map.of("forgotten",true); }
  @GetMapping("/manifest") public FoliData.Manifest manifest(@RequestParam String documentId, Authentication auth) {
    return index.read(documentId,user(auth),ignored -> {}).manifest();
  }
  @GetMapping("/source") public Map<String,Object> source(@RequestParam String documentId, @RequestParam String hash,
      @RequestParam int page, Authentication auth) {
    var snapshot = index.read(documentId,user(auth),ignored -> {});
    requireHash(hash,snapshot.hash());
    if (page<1 || page>snapshot.pages().size()) throw AuthorizedDocumentResolver.missing();
    return Map.of("document",snapshot.document(),"sourceHash",snapshot.hash(),"page",snapshot.pages().get(page-1));
  }
  @GetMapping(value="/page", produces="image/png") public ResponseEntity<byte[]> page(@RequestParam String documentId,
      @RequestParam String hash, @RequestParam int page, Authentication auth) {
    var owner = user(auth); var source = resolver.open(documentId,owner); requireHash(hash,source.hash());
    byte[] image = gate.reading(() -> extraction.renderPage(source,page));
    requireHash(hash,resolver.open(documentId,owner).hash());
    return ResponseEntity.ok().contentType(MediaType.IMAGE_PNG).body(image);
  }
  static void requireHash(String requested, String actual) {
    if (requested == null || !requested.equals(actual))
      throw AuthorizedDocumentResolver.failure("SOURCE_CHANGED", "Source changed or citation expired. Read the current source again.");
  }
}
