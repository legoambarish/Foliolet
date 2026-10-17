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
    var out=new LinkedHashMap<String,Object>();
    out.put("method",r==null?"MANUAL_UPLOAD":r.method);out.put("indicator",r==null?"INCONCLUSIVE":r.indicator);
    out.put("lineage",r==null?"NOT_ASSESSED":r.lineage);out.put("issuer","NOT_VERIFIED");
    if(r!=null){out.put("state",r.state);out.put("stage",r.stage);}
    out.put("checks",checks(r));out.put("stamps",stamps(r));return out;
  }
  public Map<String,String> checks(IntakeRecord r) {
    String qr="NOT_CHECKED",branding="NOT_CHECKED",signature="NOT_CHECKED";
    if(r!=null && r.encryptedReport!=null) {
      var report=open(r.encryptedReport,r.credentialId,"report",Map.class);
      var node=json.valueToTree(report).path("indicators");
      signature=node.path("pdfSignature").asText("NOT_CHECKED");
      qr="INCONCLUSIVE";branding="INCONCLUSIVE";
      for(var page:node.path("pages")) {
        if(page.path("logo").asBoolean(false))branding="PASSED";
        for(var code:page.path("qr"))if(com.sih26190.dms.foli.IntakeIndicators.associated(code.path("kind").asText()))qr="PASSED";
      }
      if(node.path("warnings").toString().contains("Text/CSV")){qr="NOT_APPLICABLE";branding="NOT_APPLICABLE";}
    }
    String imported=r!=null && "WATCHER_ASSISTED".equals(r.method) && r.observationId!=null && r.sessionId!=null?"PASSED":"NOT_APPLICABLE";
    return Map.of("qr",qr,"branding",branding,"imported",imported,"pdfSignature",signature,"issuer","UNVERIFIED");
  }
  private List<Map<String,String>> stamps(IntakeRecord r) {
    var c=checks(r);var result=new ArrayList<Map<String,String>>();
    result.add(stamp("qr","DigiLocker-associated QR",c.get("qr"),"Decoded supported format only; copied or forged payloads do not prove authenticity."));
    result.add(stamp("branding","DigiLocker branding",c.get("branding"),"Matching graphic only; branding can be copied."));
    result.add(stamp("imported","Imported with Foliolet",c.get("imported"),"Recorded watcher-assisted import; the originating website is not authenticated."));
    result.add(stamp("pdfSignature","PDF signature integrity",c.get("pdfSignature"),"Supported signature mathematics and current-file coverage only. Certificate issuer authority is not established."));
    String lineage=r==null?"NOT_ASSESSED":r.lineage;
    result.add(stamp("modified","Facts modified after extraction",lineage.equals("SUGGESTIONS_MODIFIED")?"MODIFIED":lineage.equals("SUGGESTIONS_UNMODIFIED")?"UNCHANGED":lineage,
        "Server comparison with the preserved extraction baseline. Unassessed or stale is not unchanged."));
    result.add(stamp("issuer","Issuer authority","UNVERIFIED","No independently trusted issuer authority has been established."));
    return List.copyOf(result);
  }
  private static Map<String,String> stamp(String id,String label,String state,String detail) {
    return Map.of("id",id,"label",label,"state",state,"detail",detail,"tone",state.equals("PASSED")?"pass":state.equals("FAILED")?"fail":state.equals("MODIFIED")?"caution":"quiet",
        "display",state.equals("PASSED")?"Passed":state.equals("UNCHANGED")?"Unchanged":state.replace('_',' ').toLowerCase(Locale.ROOT));
  }
  public WalletDtos.IntakeStatus disclosure(CredentialDocument d,List<MerkleTreeService.RevealedClaim> claims,String sourceHash,boolean includeDocument) {
    var r=records.findById(d.id).orElse(null);var b=r==null?null:baseline(r);
    boolean current=r!=null && Objects.equals(sourceHash,r.sourceHash) && Integer.toString(d.version).equals(r.sourceVersion);
    boolean comparable=current && b!=null && Objects.equals(b.sourceHash(),sourceHash) && Integer.toString(d.version).equals(b.version());
    var original=comparable?canonical(b.fields().stream().map(FactSuggestions.Candidate::claim).toList()):Map.<String,ClaimInput>of();
    var facts=new ArrayList<WalletDtos.FactStatus>();
    for(var claim:claims) {
      var l=claim.leaf();String lineage="NOT_ASSESSED",support="NOT_ASSESSED";
      if(!l.derivedFrom().isEmpty()){lineage="DERIVED";support="DERIVED";}
      else if(b!=null && !comparable)lineage="STALE_SOURCE";
      else if(comparable) {
        var old=original.get(l.path());var now=new ClaimInput(l.path(),l.label(),l.type(),l.value());
        lineage=old==null?"ADDED":old.equals(now)?"UNCHANGED":"EDITED";
        if(old!=null) {
          var field=b.fields().stream().filter(f -> canonical.path(f.path()).equals(l.path())).findFirst().orElseThrow();
          // Support describes the original suggestion, never automatic support for a holder edit.
          support=field.support()==null?"NOT_ASSESSED":field.support().quality();
        }
      }
      facts.add(new WalletDtos.FactStatus(l.index(),lineage,support));
    }
    var c=checks(current?r:null);String hidden="NOT_DISCLOSED";
    return new WalletDtos.IntakeStatus("intake-status-v1",includeDocument?c.get("qr"):hidden,
        includeDocument?c.get("branding"):hidden,includeDocument?c.get("imported"):hidden,includeDocument?c.get("pdfSignature"):hidden,"UNVERIFIED",List.copyOf(facts));
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
    else if(!Objects.equals(b.sourceHash(),r.sourceHash) || !sourceMatches(d,b.sourceHash()) || !b.version().equals(Integer.toString(d.version))) r.lineage="STALE_SOURCE";
    else {
      var change=compare(b,fields);
      r.lineage=change.edited()+change.added()+change.removed()==0?"SUGGESTIONS_UNMODIFIED":"SUGGESTIONS_MODIFIED";
      r.encryptedChanges=seal(change,d.id,"changes");
    }
    save(r);
  }
  private boolean sourceMatches(CredentialDocument d,String hash) {
    try{return Objects.equals(hash,PrivateVault.sha256(vault.read(d.filePath,d.id)));}
    catch(Exception e){return false;}
  }
}
