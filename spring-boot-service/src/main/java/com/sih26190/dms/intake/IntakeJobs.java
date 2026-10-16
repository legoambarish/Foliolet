package com.sih26190.dms.intake;

import com.sih26190.dms.foli.*;
import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;
import com.sih26190.dms.selective.*;
import com.sih26190.dms.selective.repository.CredentialDocumentRepository;
import jakarta.annotation.PreDestroy;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import org.springframework.http.HttpStatus;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;

/** Separately authorized suggestions. Foli's general assistant retains its read-only boundary. */
@Service
public class IntakeJobs {
  private final ThreadPoolExecutor executor=new ThreadPoolExecutor(1,1,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(4),r -> {
    var t=new Thread(r,"private-intake-reader"); t.setDaemon(true); return t;
  });
  private final Map<String,Future<?>> futures=new ConcurrentHashMap<>();
  private final Map<Long,ArrayDeque<Long>> requests=new HashMap<>();
  private final WalletService wallet;
  private final CredentialDocumentRepository docs;
  private final IntakeMetadata metadata;
  private final UserRepository users;
  private final AuthorizedDocumentResolver resolver;
  private final FoliReader reader;
  private final FoliWorkGate gate;
  private final FactSuggestions suggestions;
  private final FoliProperties config;
  private final TransactionTemplate tx;
  public IntakeJobs(WalletService wallet,CredentialDocumentRepository docs,IntakeMetadata metadata,UserRepository users,
      AuthorizedDocumentResolver resolver,FoliReader reader,FoliWorkGate gate,FactSuggestions suggestions,FoliProperties config,
      org.springframework.transaction.PlatformTransactionManager manager) {
    this.wallet=wallet; this.docs=docs; this.metadata=metadata; this.users=users; this.resolver=resolver;
    this.reader=reader; this.gate=gate; this.suggestions=suggestions; this.config=config; tx=new TransactionTemplate(manager);
  }
  public synchronized Map<String,Object> start(String id,User owner,boolean retry) {
    var d=wallet.owned(id,owner);
    if(!d.status.equals("DRAFT")) throw new IllegalArgumentException("Only draft documents can be analyzed");
    var existing=futures.get(id);
    if(existing!=null && !existing.isDone()) return get(id,owner);
    var bucket=requests.computeIfAbsent(owner.getId(),x -> new ArrayDeque<>());
    long now=System.currentTimeMillis();
    while(!bucket.isEmpty() && bucket.peekFirst()<now-60000) bucket.removeFirst();
    if(bucket.size()>=6) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS,"Wait a minute before starting another document reading.");
    boolean accepted=Boolean.TRUE.equals(tx.execute(status -> {
      var locked=docs.locked(id).orElseThrow(); var r=metadata.record(locked);
      if(!locked.status.equals("DRAFT")) throw new IllegalArgumentException("Only draft documents can be analyzed");
      if(r.attempts>0 && !retry) return false;
      if(r.attempts>=5) throw new IllegalArgumentException("This version reached its five-attempt reading budget. Manual facts remain available.");
      r.state="QUEUED"; r.stage="Waiting for local reading"; r.startedAt=Instant.now(); r.attempts++; metadata.save(r);
      return true;
    }));
    // A prior terminal job is never automatically replaced; retry is an explicit owner action.
    if(!accepted) return get(id,owner);
    int attempt=metadata.record(d).attempts;
    try { futures.put(id,executor.submit(() -> run(id,owner.getId(),attempt))); bucket.addLast(now); }
    catch(RejectedExecutionException e) { finishError(id,"BUSY","The local queue is full. Original saved; retry reading or enter facts manually."); }
    return get(id,owner);
  }
  public void automatically(String id,User owner) {
    try { start(id,owner,false); }
    catch(RuntimeException e) {
      // Auto-enrollment must acknowledge its saved original even when a rate or
      // availability gate prevents scheduling. Never leave a fictitious queued job.
      tx.executeWithoutResult(status -> {
        var d=docs.locked(id).orElseThrow();var r=metadata.record(d);
        if(d.status.equals("DRAFT") && r.attempts==0) {
          r.state="READING_UNAVAILABLE";r.stage="Original saved. Local reading could not start; retry shortly or enter facts manually.";metadata.save(r);
        }
      });
    }
  }
  public synchronized Map<String,Object> get(String id,User owner) {
    var d=wallet.owned(id,owner); var r=metadata.record(d);
    if(Set.of("RUNNING","QUEUED").contains(r.state) && r.attempts>0) {
      var f=futures.get(id);
      if(f==null) finishError(id,"INTERRUPTED","Reading was interrupted by a restart. Original saved; retry or enter facts manually.");
    }
    if(r.sourceHash!=null) {
      var current=resolver.open("wallet:"+id,owner);
      if(!r.sourceHash.equals(current.hash()) || !Integer.toString(d.version).equals(r.sourceVersion))
        throw new ResponseStatusException(HttpStatus.CONFLICT,"The source version changed. Historical suggestions cannot be used.");
    }
    return metadata.detail(d);
  }
  private void run(String id,long ownerId,int attempt) {
    try {
      User owner=users.findById(ownerId).orElseThrow();
      var source=resolver.open("wallet:"+id,owner);
      progress(id,attempt,"Reading document");
      var inspected=inspect(id,attempt,source);
      var report=new LinkedHashMap<String,Object>();
      report.put("manifest",inspected.snapshot().manifest()); report.put("indicators",inspected.indicators());
      report.put("model",config.getModel()); report.put("prompt",FactSuggestions.VERSION);
      FactSuggestions.Result proposed=null; String state="READY",stage="Suggestions ready";
      try {
        if(!config.isEnabled()) throw new FoliException(HttpStatus.SERVICE_UNAVAILABLE,"DISABLED","Local suggestions disabled. Enter facts manually.");
        proposed=suggestions.suggest(inspected.snapshot(),s -> progress(id,attempt,s));
        report.put("discarded",proposed.discarded()); report.put("suggestionWarnings",proposed.warnings());
        if(proposed.fields().isEmpty()) { state="NO_VERIFIABLE_FIELDS"; stage="No verifiable fields found · enter facts manually"; }
        else if(proposed.partial() || !inspected.snapshot().manifest().complete()) { state="PARTIAL"; stage="Partial reading · check coverage and original"; }
      } catch(FoliException e) {
        state=e.code().equals("OFFLINE") || e.code().equals("MODEL_MISSING")?"MODEL_OFFLINE":e.code().contains("TIMEOUT")?"TIMED_OUT":"MODEL_UNAVAILABLE";
        stage=e.getReason(); report.put("modelCode",e.code());
      } catch(IllegalArgumentException e) { state="NO_VERIFIABLE_FIELDS"; stage="The local proposal could not be validated. Enter facts manually or retry."; }
      var current=resolver.open("wallet:"+id,users.findById(ownerId).orElseThrow());
      if(!current.hash().equals(source.hash()) || !current.document().version().equals(source.document().version())) throw new IllegalStateException("Changed source");
      final var fields=proposed; final var finalState=state; final var finalStage=stage;
      tx.executeWithoutResult(status -> {
        var d=docs.locked(id).orElseThrow(); var r=metadata.record(d);
        if(r.attempts!=attempt || !Set.of("QUEUED","RUNNING").contains(r.state)) return;
        if(r.encryptedReport!=null) {
          var history=r.encryptedHistory==null?new ArrayList<>():new ArrayList<>(metadata.open(r.encryptedHistory,id,"history",List.class));
          history.add(metadata.open(r.encryptedReport,id,"report",Map.class)); r.encryptedHistory=metadata.seal(history,id,"history");
        }
        r.sourceHash=source.hash(); r.sourceVersion=source.document().version();
        r.indicator=inspected.indicators().status(); r.state=finalState; r.stage=finalStage;
        r.encryptedReport=metadata.seal(report,id,"report");
        // First valid source-aligned proposal is write-once; no late baseline after manual confirmation.
        if(r.encryptedBaseline==null && r.confirmedAt==null && d.status.equals("DRAFT") && d.merkleRoot==null
            && fields!=null && !fields.fields().isEmpty()) {
          var baseline=new IntakeMetadata.Baseline(source.hash(),source.document().version(),inspected.snapshot().manifest().extractorVersion(),
              inspected.snapshot().manifest().ocrEngine(),config.getModel(),FactSuggestions.VERSION,fields.fields());
          r.encryptedBaseline=metadata.seal(baseline,id,"baseline");
        }
        metadata.save(r);
      });
    } catch(FoliException e) { finishError(id,attempt,e.code(),e.getReason());
    } catch(CancellationException e) { finishError(id,attempt,"TIMED_OUT","Reading stopped or exceeded its time budget. Original saved.");
    } catch(Exception e) { finishError(id,attempt,"READING_FAILED","Local reading failed. Original saved; retry or enter facts manually."); }
  }
  private FoliReader.Response inspect(String id,int attempt,FoliData.Source source) {
    long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(45);
    while(true) {
      try {return gate.reading(() -> reader.inspect(source,stage -> progress(id,attempt,stage)));}
      catch(FoliException e) {
        if(!e.code().equals("BUSY") || System.nanoTime()>deadline) throw e;
        progress(id,attempt,"Waiting for local reader");
        try {Thread.sleep(500);} catch(InterruptedException interrupted) {Thread.currentThread().interrupt();throw new CancellationException();}
      }
    }
  }
  private void progress(String id,int attempt,String stage) {
    if(Thread.currentThread().isInterrupted()) throw new CancellationException();
    tx.executeWithoutResult(status -> {
      var d=docs.locked(id).orElseThrow(); var r=metadata.record(d);
      if(r.attempts!=attempt || !Set.of("QUEUED","RUNNING").contains(r.state) || r.startedAt==null || r.startedAt.isBefore(Instant.now().minusSeconds(300))) throw new CancellationException();
      r.state="RUNNING"; r.stage=stage; metadata.save(r);
    });
  }
  private void finishError(String id,String code,String message) {
    finishError(id,-1,code,message);
  }
  private void finishError(String id,int attempt,String code,String message) {
    tx.executeWithoutResult(status -> {
      var d=docs.locked(id).orElse(null); if(d==null) return;
      var r=metadata.record(d);
      if(attempt>=0 && (r.attempts!=attempt || !Set.of("QUEUED","RUNNING").contains(r.state))) return;
      r.state=code.contains("TIMEOUT")?"TIMED_OUT":code; r.stage=message; metadata.save(r);
    });
  }
  @Scheduled(fixedDelay=15000) public synchronized void cleanup() {
    futures.entrySet().removeIf(e -> {
      if(e.getValue().isDone()) return true;
      var d=docs.findById(e.getKey()).orElse(null);
      var started=d==null?null:metadata.record(d).startedAt;
      if(started!=null && started.isBefore(Instant.now().minusSeconds(300))) {
        e.getValue().cancel(true); finishError(e.getKey(),"TIMED_OUT","Reading exceeded five minutes. Original saved; retry or enter facts manually."); return true;
      }
      return false;
    });
    long now=System.currentTimeMillis(); requests.entrySet().removeIf(e -> e.getValue().isEmpty() || e.getValue().peekLast()<now-60000);
  }
  @PreDestroy public void close() { futures.values().forEach(f -> f.cancel(true)); executor.shutdownNow(); }
}
