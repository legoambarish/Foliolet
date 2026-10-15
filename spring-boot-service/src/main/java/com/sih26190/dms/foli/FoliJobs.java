package com.sih26190.dms.foli;

import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;
import jakarta.annotation.PreDestroy;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import jakarta.validation.constraints.Pattern;
import java.util.*;
import java.util.concurrent.*;
import org.springframework.http.HttpStatus;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import static com.sih26190.dms.foli.FoliData.*;
import com.sih26190.dms.foli.FoliChatService.Turn;

@Service
public class FoliJobs {
  public record Request(@Size(max=100) String documentId, @Size(max=4000) String question,
      @Pattern(regexp="index|chat|review") String mode,
      @Size(max=6) List<@Valid Turn> history,
      @Pattern(regexp="[0-9a-f]{64}") String sourceHash) {}
  private static class Job {
    final String id=UUID.randomUUID().toString(); final long owner,created=System.currentTimeMillis();
    final String documentId,hash,version; volatile String state="QUEUED",stage="Queued",code="",message="";
    volatile Object result; volatile Future<?> future;
    Job(long owner,String documentId,String hash,String version) { this.owner=owner; this.documentId=documentId; this.hash=hash; this.version=version; }
    boolean active() { return state.equals("QUEUED") || state.equals("RUNNING"); }
  }
  private final Map<String,Job> jobs=new ConcurrentHashMap<>();
  private final Map<Long,ArrayDeque<Long>> requests=new HashMap<>();
  private final ThreadPoolExecutor executor=new ThreadPoolExecutor(1,1,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(4),r -> {
    var thread=new Thread(r,"foli-private-worker"); thread.setDaemon(true); return thread;
  });
  private final AuthorizedDocumentResolver resolver;
  private final FoliIndex index;
  private final FoliChatService chat;
  private final UserRepository users;
  private final FoliProperties config;
  public FoliJobs(AuthorizedDocumentResolver resolver,FoliIndex index,FoliChatService chat,UserRepository users,FoliProperties config) {
    this.resolver=resolver; this.index=index; this.chat=chat; this.users=users; this.config=config;
  }
  public synchronized Map<String,Object> create(Request request,User user) {
    cleanup();
    String mode=request.mode()==null?"chat":request.mode();
    if (request.question()!=null && request.question().length()>4000 || request.history()!=null && request.history().size()>6)
      throw new IllegalArgumentException();
    if (!mode.equals("index") && (request.question()==null || request.question().isBlank())) throw new IllegalArgumentException();
    if (mode.equals("review")) throw new FoliException(HttpStatus.BAD_REQUEST,"MODE_UNAVAILABLE","Document-wide review is not available in this build yet.");
    if (jobs.size()>=32 || jobs.values().stream().filter(j -> j.owner==user.getId() && j.active()).count()>=2)
      throw new FoliException(HttpStatus.TOO_MANY_REQUESTS,"BUSY","Foli already has pending work. Wait or stop a request.");
    var bucket=requests.computeIfAbsent(user.getId(),ignored -> new ArrayDeque<>());
    while(!bucket.isEmpty() && bucket.peekFirst()<System.currentTimeMillis()-60000) bucket.removeFirst();
    if (bucket.size()>=10) throw new FoliException(HttpStatus.TOO_MANY_REQUESTS,"RATE_LIMIT","Please wait a minute before sending more questions.");
    String id=request.documentId()==null || request.documentId().isBlank()?null:request.documentId();
    if (id==null && mode.equals("index")) throw new IllegalArgumentException();
    Source source=id==null?null:resolver.open(id,user);
    if (source!=null && request.sourceHash()!=null) FoliController.requireHash(request.sourceHash(),source.hash());
    var job=new Job(user.getId(),id,source==null?"":source.hash(),source==null?"":source.document().version());
    jobs.put(job.id,job);
    try { job.future=executor.submit(() -> execute(job,request,mode)); }
    catch(RejectedExecutionException e) { jobs.remove(job.id); throw new FoliException(HttpStatus.TOO_MANY_REQUESTS,"BUSY","Foli's local queue is full. Retry shortly."); }
    bucket.addLast(System.currentTimeMillis()); return view(job);
  }

  private void execute(Job job,Request request,String mode) {
    try {
      if (!job.active()) return;
      job.state="RUNNING";
      User user=users.findById(job.owner).orElseThrow(AuthorizedDocumentResolver::missing);
      Snapshot source=job.documentId==null?null:index.read(job.documentId,user,stage -> progress(job,stage));
      if (source!=null) {
        FoliController.requireHash(job.hash,source.hash());
        if (!job.version.equals(source.document().version())) throw AuthorizedDocumentResolver.failure("SOURCE_CHANGED","Document version changed. Select it again.");
      }
      Object result=mode.equals("index")?source.manifest():chat.chat(request.question(),request.history(),source,stage -> progress(job,stage));
      progress(job,"Checking current source access");
      current(job,user);
      synchronized(job) { if(job.active()) { job.result=result; job.state="COMPLETE"; job.stage="Done"; } }
    } catch(CancellationException e) { cancel(job);
    } catch(FoliException e) { fail(job,e.code(),e.getReason());
    } catch(Exception e) { fail(job,"UNAVAILABLE","Foli could not complete the request. No document or trust data was changed."); }
  }
  private void progress(Job job,String stage) {
    FoliExtractionService.checkCancel();
    if (!job.active() || System.currentTimeMillis()-job.created>300000) throw new CancellationException();
    job.stage=stage;
  }
  private void current(Job job,User user) {
    if (job.documentId==null) return;
    Source current=resolver.open(job.documentId,user);
    FoliController.requireHash(job.hash,current.hash());
    if (!job.version.equals(current.document().version())) throw AuthorizedDocumentResolver.failure("SOURCE_CHANGED","Document version changed. Read it again.");
  }
  public Map<String,Object> get(String id,User user) {
    var job=owned(id,user);
    try { current(job,user); }
    catch(RuntimeException e) { cancel(job); jobs.remove(id); throw e; }
    return view(job);
  }
  public Map<String,Object> stop(String id,User user) { var job=owned(id,user); cancel(job); return view(job); }
  public void forget(User user) {
    jobs.values().removeIf(j -> { if(j.owner!=user.getId()) return false; cancel(j); return true; }); index.forget(user);
  }
  private Job owned(String id,User user) {
    var job=jobs.get(id);
    if(job==null || job.owner!=user.getId() || job.created+config.getRetentionSeconds()*1000L<System.currentTimeMillis())
      throw AuthorizedDocumentResolver.missing();
    return job;
  }
  private static void cancel(Job job) { synchronized(job) { job.state="CANCELLED"; job.stage="Stopped"; job.result=null; if(job.future!=null) job.future.cancel(true); } }
  private static void fail(Job job,String code,String message) { synchronized(job) { if(job.active()) { job.state="ERROR"; job.stage="Failed"; job.code=code; job.message=message; job.result=null; } } }
  private static Map<String,Object> view(Job job) {
    var out=new LinkedHashMap<String,Object>(); out.put("id",job.id); out.put("state",job.state); out.put("stage",job.stage);
    out.put("documentId",job.documentId); out.put("sourceHash",job.hash); out.put("code",job.code); out.put("message",job.message);
    out.put("result",job.state.equals("COMPLETE")?job.result:null); return out;
  }
  @Scheduled(fixedDelay=15000) public synchronized void cleanup() {
    long now=System.currentTimeMillis();
    jobs.values().removeIf(j -> { if(j.created+config.getRetentionSeconds()*1000L>=now) { if(j.active() && now-j.created>300000) cancel(j); return false; } cancel(j); return true; });
    requests.entrySet().removeIf(e -> e.getValue().isEmpty() || e.getValue().peekLast()<now-60000);
    executor.purge();
  }
  @PreDestroy public void close() { jobs.values().forEach(FoliJobs::cancel); jobs.clear(); executor.shutdownNow(); }
}
