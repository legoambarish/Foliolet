package com.sih26190.dms.intake;

import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;
import java.util.*;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
public class IntakeController {
  private final IntakeSessions sessions;
  private final IntakeJobs jobs;
  private final UserRepository users;
  public IntakeController(IntakeSessions sessions,IntakeJobs jobs,UserRepository users) { this.sessions=sessions; this.jobs=jobs; this.users=users; }
  private User owner(Authentication auth) { return users.findByUsername(auth.getName()).orElseThrow(IntakeSessions::missing); }
  @GetMapping("/api/wallet/intake/sessions") public Object list(Authentication auth) { return sessions.list(owner(auth)); }
  @PostMapping("/api/wallet/intake/sessions") public Object arm(@RequestBody Map<String,String> body,Authentication auth) {
    if(!Set.of("folder").equals(body.keySet())) throw new IllegalArgumentException("Choose an intake folder");
    return sessions.arm(owner(auth),body.get("folder"));
  }
  @PostMapping("/api/wallet/intake/sessions/{id}/stop") public Object stop(@PathVariable String id,Authentication auth) { sessions.stop(id,owner(auth)); return Map.of("active",false); }
  @PostMapping("/api/wallet/intake/sessions/{id}/import") public Object importSelected(@PathVariable String id,
      @RequestParam String folderHash,@RequestParam String relativePath,@RequestParam MultipartFile file,Authentication auth) {
    var holder=owner(auth); var result=sessions.importSelected(id,folderHash,relativePath,file,holder);
    jobs.automatically(result.get("id").toString(),holder); return result;
  }
  @GetMapping("/api/wallet/intake/documents/{id}") public Object status(@PathVariable String id,Authentication auth) { return jobs.get(id,owner(auth)); }
  @PostMapping("/api/wallet/intake/documents/{id}/retry") public Object retry(@PathVariable String id,Authentication auth) { return jobs.start(id,owner(auth),true); }
  @PostMapping("/api/intake-agent/heartbeat") public Object heartbeat(@RequestParam String folderHash,Authentication auth) { return sessions.heartbeat(auth.getName(),folderHash); }
  @PostMapping("/api/intake-agent/upload") public Object upload(@RequestParam String folderHash,@RequestParam String relativePath,
      @RequestParam String sha256,@RequestParam String observationId,@RequestParam MultipartFile file,Authentication auth) {
    var result=sessions.upload(auth.getName(),folderHash,relativePath,sha256,observationId,file);
    jobs.automatically(result.get("id").toString(),sessions.companionOwner(auth.getName()));
    return result;
  }
}
