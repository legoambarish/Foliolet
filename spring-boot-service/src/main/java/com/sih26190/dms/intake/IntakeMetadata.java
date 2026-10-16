package com.sih26190.dms.intake;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sih26190.dms.selective.*;
import com.sih26190.dms.selective.WalletDtos.ClaimInput;
import com.sih26190.dms.selective.model.CredentialDocument;
import java.time.Instant;
import java.util.*;
import org.springframework.stereotype.Service;

/** Called under the credential row lock for mutations. No wallet or model authority. */
@Service
public class IntakeMetadata {
  public record Changes(int edited, int added, int removed) {}
  public record Baseline(String sourceHash, String version, String extractor, String ocrEngine, String model,
                         String prompt, List<FactSuggestions.Candidate> fields) {}
  private final IntakeRecordRepository records;
  private final PrivateVault vault;
  private final ClaimCanonicalizer canonical;
  private final ObjectMapper json = new ObjectMapper();
  public IntakeMetadata(IntakeRecordRepository records, PrivateVault vault, ClaimCanonicalizer canonical) {
    this.records=records; this.vault=vault; this.canonical=canonical;
  }
  public IntakeRecord record(CredentialDocument d) {
    var r=records.findById(d.id).orElseGet(() -> { var n=new IntakeRecord(); n.credentialId=d.id; n.ownerId=d.ownerId; return n; });
    if(!r.ownerId.equals(d.ownerId)) throw new IllegalStateException("Invalid intake owner");
    return r;
  }
  public void save(IntakeRecord r) { r.updatedAt=Instant.now(); records.save(r); }
  public String seal(Object value,String id,String purpose) {
    try { return vault.seal(json.writeValueAsString(value),"intake:"+id+":"+purpose); }
    catch(Exception e) { throw new IllegalStateException("Private intake storage failed"); }
  }
  public <T> T open(String value,String id,String purpose,Class<T> type) {
    try { return json.readValue(vault.open(value,"intake:"+id+":"+purpose),type); }
    catch(Exception e) { throw new IllegalStateException("Private intake data unavailable"); }
  }
  public Baseline baseline(IntakeRecord r) {
    return r.encryptedBaseline==null?null:open(r.encryptedBaseline,r.credentialId,"baseline",Baseline.class);
  }
  public Map<String,Object> summary(String id) {
    var r=records.findById(id).orElse(null);
    if(r==null) return Map.of("method","MANUAL_UPLOAD","indicator","INCONCLUSIVE","lineage","NOT_ASSESSED","issuer","NOT_VERIFIED");
    return Map.of("method",r.method,"state",r.state,"stage",r.stage,"indicator",r.indicator,
        "lineage",r.lineage,"issuer","NOT_VERIFIED");
  }
  public Map<String,Object> detail(CredentialDocument d) {
    var out=new LinkedHashMap<>(summary(d.id));
    String filename=d.originalFilename==null?"":d.originalFilename.toLowerCase(Locale.ROOT);
    out.put("format",filename.endsWith(".pdf")?"pdf":filename.endsWith(".txt")?"txt":filename.endsWith(".csv")?"csv":"unsupported");
    var r=records.findById(d.id).orElse(null);
    if(r!=null) {
      Map report=r.encryptedReport==null?Map.of():open(r.encryptedReport,d.id,"report",Map.class);
      if(!report.isEmpty()) out.put("report",report);
      var b=baseline(r);
      // A later reading can be reviewed even after manual confirmation; it never rewrites the first baseline.
      out.put("fields",b==null?report.getOrDefault("currentFields",List.of()):b.fields());
      if(r.encryptedChanges!=null) out.put("changes",open(r.encryptedChanges,d.id,"changes",Changes.class));
      out.put("attempts",r.attempts);
    }
    return out;
  }
  public Map<String,ClaimInput> canonical(List<ClaimInput> fields) {
    if(fields==null || fields.size()>64) throw new IllegalArgumentException("Use at most 64 facts");
    var result=new TreeMap<String,ClaimInput>();
    for(var c:fields) {
      var n=new ClaimInput(canonical.path(c.path()),canonical.text(c.label(),100),c.type(),canonical.value(c.type(),c.value()));
      if(result.put(n.path(),n)!=null) throw new IllegalArgumentException("Duplicate fact path");
    }
    return result;
  }
  public Changes compare(Baseline b,List<ClaimInput> fields) {
    var old=canonical(b.fields().stream().map(FactSuggestions.Candidate::claim).toList());
    var now=canonical(fields);
    int edited=0,added=0,removed=0;
    for(var p:old.keySet()) { if(!now.containsKey(p)) removed++; else if(!old.get(p).equals(now.get(p))) edited++; }
    for(var p:now.keySet()) if(!old.containsKey(p)) added++;
    return new Changes(edited,added,removed);
  }
  public void confirmed(CredentialDocument d,List<ClaimInput> fields) {
    var r=record(d); var b=baseline(r);
    r.confirmedAt=Instant.now();
    if(b==null || b.fields().isEmpty()) r.lineage="NOT_ASSESSED";
    else if(!Objects.equals(b.sourceHash(),r.sourceHash) || !b.version().equals(Integer.toString(d.version))) r.lineage="STALE_SOURCE";
    else {
      var change=compare(b,fields);
      r.lineage=change.edited()+change.added()+change.removed()==0?"SUGGESTIONS_UNMODIFIED":"SUGGESTIONS_MODIFIED";
      r.encryptedChanges=seal(change,d.id,"changes");
    }
    save(r);
  }
}
