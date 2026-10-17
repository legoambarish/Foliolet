package com.sih26190.dms.intake;

import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;
import com.sih26190.dms.selective.*;
import com.sih26190.dms.selective.repository.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.time.Instant;
import java.util.*;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

@Service
public class IntakeSessions {
  private final IntakeSessionRepository sessions;
  private final IntakeReceiptRepository receipts;
  private final IntegrityAgentRepository agents;
  private final FirstSeenObservationRepository observations;
  private final IntegrityService integrity;
  private final WalletService wallet;
  private final IntakeMetadata metadata;
  private final UserRepository users;
  private final TransactionTemplate tx;
  public IntakeSessions(IntakeSessionRepository sessions,IntakeReceiptRepository receipts,IntegrityAgentRepository agents,
      FirstSeenObservationRepository observations,IntegrityService integrity,WalletService wallet,IntakeMetadata metadata,
      UserRepository users,org.springframework.transaction.PlatformTransactionManager manager) {
    this.sessions=sessions; this.receipts=receipts; this.agents=agents; this.observations=observations;
    this.integrity=integrity; this.wallet=wallet; this.metadata=metadata; this.users=users; tx=new TransactionTemplate(manager);
  }
  public static String fingerprint(String folder) { return PrivateVault.sha256(folder.getBytes(StandardCharsets.UTF_8)); }
  public synchronized Map<String,Object> arm(User owner,String folder) {
    if(folder==null || folder.length()>500 || folder.chars().anyMatch(Character::isISOControl)) throw new IllegalArgumentException("Choose a dedicated absolute intake folder");
    Path path=Path.of(folder).toAbsolutePath().normalize();
    if(!Path.of(folder).isAbsolute() || path.getNameCount()<3 || !path.toString().equals(folder)
        || Set.of("downloads","desktop","documents","users","windows","system32").contains(path.getFileName().toString().toLowerCase(Locale.ROOT)))
      throw new IllegalArgumentException("Choose a dedicated subfolder, such as Downloads/Foliolet Intake");
    return tx.execute(status -> {
      var priorSessions=sessions.findByOwnerIdOrderByCreatedAtDesc(owner.getId());
      if(priorSessions.stream().filter(s -> s.createdAt.isAfter(Instant.now().minusSeconds(60))).count()>=6)
        throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS,"Wait a minute before arming another intake session");
      // Re-arming replaces this owner's capabilities, never another holder's state.
      for(var prior:priorSessions) if(!prior.revoked) {
        var locked=sessions.locked(prior.id).orElseThrow(); locked.revoked=true; sessions.save(locked);
        integrity.revoke(owner,locked.agentId);
      }
      var agent=integrity.create(owner,"Assisted intake session");
      byte[] random=new byte[32]; new SecureRandom().nextBytes(random); String token=HexFormat.of().formatHex(random);
      var session=new IntakeSession(); session.id=UUID.randomUUID().toString(); session.ownerId=owner.getId();
      session.agentId=agent.get("agentId").toString(); session.tokenHash=fingerprint(token); session.folderHash=fingerprint(folder);
      session.encryptedFolder=metadata.seal(folder,session.id,"folder"); session.createdAt=Instant.now(); session.expiresAt=null;
      sessions.save(session);
      var config=new LinkedHashMap<String,Object>(agent); config.put("sessionId",session.id); config.put("token",token);
      config.put("folder",folder); config.put("folderHash",session.folderHash); config.put("expiresAt",session.expiresAt);
      config.put("createdAt",session.createdAt);
      config.put("lifetime","app"); config.put("maxBytes",20*1024*1024); config.put("maxFiles",0); config.put("extensions",List.of(".pdf",".txt",".csv"));
      return config;
    });
  }
  public IntakeSession authenticate(String token) {
    if(token==null || !token.matches("[0-9a-f]{64}")) throw unauthorized();
    var s=sessions.findByTokenHash(fingerprint(token)).orElseThrow(IntakeSessions::unauthorized);
    active(s);
    var a=agents.findById(s.agentId).orElseThrow(IntakeSessions::unauthorized);
    if(!a.active || !a.ownerId.equals(s.ownerId)) throw unauthorized();
    return s;
  }
  public User companionOwner(String sessionId) {
    // Called only after an accepted, session-locked upload. A simultaneous Stop
    // revokes future uploads without turning this saved receipt into a false error.
    var s=sessions.findById(sessionId).orElseThrow(IntakeSessions::unauthorized);
    return users.findById(s.ownerId).orElseThrow(IntakeSessions::unauthorized);
  }
  private void active(IntakeSession s) {
    if(s.revoked || (s.expiresAt!=null && !s.expiresAt.isAfter(Instant.now()))) throw unauthorized();
  }
  public List<Map<String,Object>> list(User owner) {
    return sessions.findByOwnerIdOrderByCreatedAtDesc(owner.getId()).stream().limit(10).map(this::view).toList();
  }
  public Map<String,Object> view(IntakeSession s) {
    boolean active=!s.revoked && (s.expiresAt==null || s.expiresAt.isAfter(Instant.now()));
    var result=new LinkedHashMap<String,Object>(); result.put("id",s.id); result.put("active",active); result.put("expiresAt",s.expiresAt);
    result.put("connected",active && s.lastSeen!=null && s.lastSeen.isAfter(Instant.now().minusSeconds(20)));
    result.put("folder",metadata.open(s.encryptedFolder,s.id,"folder",String.class)); result.put("imported",s.imported);
    result.put("documents",receipts.findBySessionId(s.id).stream().map(r -> Map.of("id",r.credentialId,"importedAt",r.importedAt)).toList());
    return result;
  }
  public void stop(String id,User owner) {
    tx.executeWithoutResult(status -> {
      var s=sessions.locked(id).orElseThrow(IntakeSessions::missing);
      if(!s.ownerId.equals(owner.getId())) throw missing();
      if(!s.revoked) { s.revoked=true; sessions.save(s); integrity.revoke(owner,s.agentId); }
    });
  }
  @org.springframework.scheduling.annotation.Scheduled(fixedDelay=15000)
  public void expire() {
    for(var s:sessions.findByRevokedFalseAndExpiresAtBefore(Instant.now()))
      users.findById(s.ownerId).ifPresent(owner -> stop(s.id,owner));
  }
  public Map<String,Object> heartbeat(String sessionId,String folderHash) {
    return tx.execute(status -> {
      var s=sessions.locked(sessionId).orElseThrow(IntakeSessions::unauthorized); active(s);
      if(!s.folderHash.equals(folderHash)) throw unauthorized();
      s.lastSeen=Instant.now(); sessions.save(s);
      var result=new LinkedHashMap<String,Object>(); result.put("active",true); result.put("expiresAt",s.expiresAt);
      result.put("remaining",s.expiresAt==null ? null : Math.max(0,10-s.imported)); return result;
    });
  }
  public Map<String,Object> upload(String sessionId,String folderHash,String relative,String hash,String observationId,MultipartFile file) {
    return receive(sessionId,folderHash,relative,hash,observationId,file,null);
  }
  public Map<String,Object> importSelected(String sessionId,String folderHash,String relative,MultipartFile file,User owner) {
    if(file.isEmpty() || file.getSize()>20*1024*1024) throw new IllegalArgumentException("Invalid intake file");
    String hash;
    try { hash=PrivateVault.sha256(file.getBytes()); } catch(Exception e) { throw new IllegalArgumentException("Cannot read intake bytes"); }
    return receive(sessionId,folderHash,relative,hash,null,file,owner);
  }
  private Map<String,Object> receive(String sessionId,String folderHash,String relative,String hash,String observationId,MultipartFile file,User selectingOwner) {
    if(relative==null || relative.length()>500 || relative.startsWith("/") || relative.contains("\\")
        || Arrays.stream(relative.split("/",-1)).anyMatch(p -> p.isEmpty() || p.startsWith(".") || !p.matches("[^<>:\"|?*\\p{Cntrl}]+")))
      throw new IllegalArgumentException("Invalid intake relative path");
    String filename=relative.substring(relative.lastIndexOf('/')+1);
    String lower=filename.toLowerCase(Locale.ROOT);
    if(!lower.matches(".+\\.(pdf|txt|csv)") || !filename.equals(file.getOriginalFilename()) || filename.length()>150)
      throw new IllegalArgumentException("Use a completed PDF, TXT or CSV file");
    if(file.isEmpty() || file.getSize()>20*1024*1024 || hash==null || !hash.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("Invalid intake file");
    byte[] bytes;
    try { bytes=file.getBytes(); } catch(Exception e) { throw new IllegalArgumentException("Cannot read intake bytes"); }
    if(bytes.length>20*1024*1024 || !PrivateVault.sha256(bytes).equals(hash)) throw new ResponseStatusException(HttpStatus.CONFLICT,"Staged bytes do not match their observed SHA-256");
    if(lower.endsWith(".pdf")) {
      String header=new String(Arrays.copyOf(bytes,Math.min(bytes.length,8)),StandardCharsets.US_ASCII);
      String tail=new String(Arrays.copyOfRange(bytes,Math.max(0,bytes.length-2048),bytes.length),StandardCharsets.ISO_8859_1);
      if(!header.startsWith("%PDF-") || !tail.contains("%%EOF")) throw new IllegalArgumentException("The download is not a complete PDF");
    }
    return tx.execute(status -> {
      var s=sessions.locked(sessionId).orElseThrow(IntakeSessions::missing);
      if(selectingOwner!=null && !s.ownerId.equals(selectingOwner.getId())) throw missing();
      active(s);
      if(!s.folderHash.equals(folderHash)) throw unauthorized();
      var a=agents.findById(s.agentId).orElseThrow(IntakeSessions::unauthorized); if(!a.active) throw unauthorized();
      String key=s.id+":"+hash;
      var prior=receipts.findById(key).orElse(null);
      if(prior!=null) return Map.of("id",prior.credentialId,"sha256",hash,"duplicate",true);
      if(s.expiresAt!=null && s.imported>=10) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS,"This session reached its ten-file limit");
      // Selection is authenticated by the holder. A file without a current-agent
      // observation is self-enrolled; it must never inherit a historical record.
      var observation=selectingOwner==null
          ? observations.findById(observationId).orElseThrow(IntakeSessions::missing)
          : observations.findFirstByAgentIdAndSha256AndFilenameOrderByReceivedAtDesc(s.agentId,hash,filename).orElse(null);
      if(observation!=null && (!observation.ownerId.equals(s.ownerId) || !observation.agentId.equals(s.agentId)
          || !observation.sha256.equals(hash) || !observation.filename.equals(filename)
          || observation.receivedAt.isBefore(s.createdAt.truncatedTo(java.time.temporal.ChronoUnit.SECONDS))
          || observation.observedAt.isBefore(s.createdAt.truncatedTo(java.time.temporal.ChronoUnit.SECONDS))))
        throw new ResponseStatusException(HttpStatus.CONFLICT,"Observation does not belong to these exact bytes and this session");
      User owner=users.findById(s.ownerId).orElseThrow(IntakeSessions::unauthorized);
      var immutable=new MultipartFile() {
        public String getName() { return "file"; }
        public String getOriginalFilename() { return filename; }
        public String getContentType() { return file.getContentType(); }
        public boolean isEmpty() { return bytes.length==0; }
        public long getSize() { return bytes.length; }
        public byte[] getBytes() { return bytes.clone(); }
        public java.io.InputStream getInputStream() { return new java.io.ByteArrayInputStream(bytes); }
        public void transferTo(java.io.File dest) throws java.io.IOException { Files.write(dest.toPath(),bytes); }
      };
      String currentObservation=observation==null ? null : observation.id;
      var enrolled=wallet.enroll(immutable,filename,"Other",currentObservation,null,owner);
      String id=enrolled.get("id").toString(); var r=metadata.record(wallet.owned(id,owner));
      r.method=observation==null ? "MANUAL_UPLOAD" : "WATCHER_ASSISTED"; r.sessionId=s.id; r.observationId=currentObservation; metadata.save(r);
      var receipt=new IntakeReceipt(); receipt.id=key; receipt.sessionId=s.id; receipt.sha256=hash; receipt.credentialId=id; receipt.importedAt=Instant.now(); receipts.save(receipt);
      s.imported++; if(selectingOwner==null) s.lastSeen=Instant.now(); sessions.save(s);
      return Map.of("id",id,"sha256",hash,"duplicate",false);
    });
  }
  static ResponseStatusException unauthorized() { return new ResponseStatusException(HttpStatus.UNAUTHORIZED,"Intake session unavailable or expired"); }
  static ResponseStatusException missing() { return new ResponseStatusException(HttpStatus.NOT_FOUND,"Intake resource not found"); }
}
