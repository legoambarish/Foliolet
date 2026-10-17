package com.sih26190.dms.foli;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Consumer;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import static com.sih26190.dms.foli.FoliData.*;

/** Untrusted PDF parsing/rendering has its own heap and a killable wall-clock boundary. */
@Service
public class FoliReader {
  static final String PROGRESS="FOLI_PROGRESS\t", RESULT="FOLI_RESULT\t";
  static final int MAX_OUTPUT=64*1024*1024;
  record Request(Source source, FoliProperties config, String mode, int page) {}
  public record Response(Snapshot snapshot, byte[] png, String code, String message, int status, IntakeIndicators.Report indicators) {
    Response(Snapshot snapshot,byte[] png,String code,String message,int status) { this(snapshot,png,code,message,status,null); }
  }
  private final FoliProperties config;
  private final ObjectMapper json=new ObjectMapper();
  public FoliReader(FoliProperties config) { this.config=config; }
  public Snapshot extract(Source source, Consumer<String> progress) { return run(source,"extract",0,progress).snapshot(); }
  public byte[] renderPage(Source source,int page) { return run(source,"render",page,ignored -> {}).png(); }
  public Response inspect(Source source,Consumer<String> progress) { return run(source,"intake",0,progress); }

  private Response run(Source source,String mode,int page,Consumer<String> progress) {
    Path scratch=null; Process child=null; Set<ProcessHandle> descendants=new HashSet<>();
    ExecutorService io=Executors.newFixedThreadPool(2,r -> { var t=new Thread(r,"foli-reader-pipe"); t.setDaemon(true); return t; });
    try {
      Path root=Path.of(config.getTempDir()).toAbsolutePath().normalize(); Files.createDirectories(root);
      scratch=Files.createTempDirectory(root,"reader-");
      // An argument file also handles Windows' command-line length ceiling. No document enters it.
      Path args=scratch.resolve("jvm.args");
      String classpath=System.getProperty("java.class.path");
      String main=FoliReaderMain.class.getName();
      boolean packaged=FoliReaderMain.class.getResource("FoliReaderMain.class").toString().contains("BOOT-INF");
      var arguments=new ArrayList<String>(List.of("-Xmx512m","-XX:+ExitOnOutOfMemoryError","-Djava.awt.headless=true"));
      if(packaged) { arguments.add("-Dloader.main="+main); main="org.springframework.boot.loader.launch.PropertiesLauncher"; }
      arguments.addAll(List.of("-cp",classpath,main));
      Files.writeString(args,arguments.stream().map(FoliReader::quoteArg).collect(java.util.stream.Collectors.joining("\n")),StandardCharsets.UTF_8);
      var workerConfig=json.readValue(json.writeValueAsBytes(config),FoliProperties.class);
      workerConfig.setTempDir(scratch.toString());
      String java=Path.of(System.getProperty("java.home"),"bin",System.getProperty("os.name").startsWith("Windows")?"java.exe":"java").toString();
      var launch=new ProcessBuilder(java,"@"+args).redirectError(ProcessBuilder.Redirect.DISCARD);
      // Do not inherit database, vault, blockchain, proxy or model credentials.
      var environment=launch.environment(); var original=new HashMap<>(environment); environment.clear();
      original.forEach((key,value) -> { if(Set.of("SYSTEMROOT","WINDIR","TEMP","TMP","PATH").contains(key.toUpperCase(Locale.ROOT))) environment.put(key,value); });
      child=launch.start();
      Process process=child;
      Future<?> writer=io.submit(() -> {
        try(var stdin=process.getOutputStream()) { json.writeValue(stdin,new Request(source,workerConfig,mode,page)); }
        catch(IOException e) { throw new UncheckedIOException(e); }
      });
      Future<Response> reader=io.submit(() -> {
        try(var input=new BufferedReader(new InputStreamReader(new LimitedInputStream(process.getInputStream()),StandardCharsets.UTF_8))) {
          Response response=null; String line;
          while((line=input.readLine())!=null) {
            if(line.startsWith(PROGRESS)) progress.accept(line.substring(PROGRESS.length()));
            if(line.startsWith(RESULT)) response=json.readValue(line.substring(RESULT.length()),Response.class);
          }
          return response;
        }
      });
      long seconds=mode.equals("render")?30:config.getExtractionTimeoutSeconds();
      long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(Math.max(1,seconds));
      while(!process.waitFor(100,TimeUnit.MILLISECONDS)) {
        process.descendants().forEach(descendants::add);
        if(System.nanoTime()>deadline) throw new FoliException(HttpStatus.UNPROCESSABLE_CONTENT,"READER_TIMEOUT","Reading exceeded the time budget. No complete review was produced.");
      }
      writer.get(2,TimeUnit.SECONDS);
      Response response=reader.get(3,TimeUnit.SECONDS);
      if(process.exitValue()!=0 || response==null) throw failed();
      if(response.code()!=null) throw new FoliException(HttpStatus.valueOf(response.status()),response.code(),response.message());
      if(mode.equals("render")?response.png()==null:response.snapshot()==null) throw failed();
      if(mode.equals("intake") && response.indicators()==null) throw failed();
      return response;
    } catch(InterruptedException e) {
      Thread.currentThread().interrupt(); throw new CancellationException("Reading cancelled");
    } catch(FoliException e) { throw e;
    } catch(Exception e) { throw failed();
    } finally {
      if(child!=null) {
        child.descendants().forEach(descendants::add);
        descendants.forEach(p -> { if(p.isAlive()) p.destroyForcibly(); });
        if(child.isAlive()) child.destroyForcibly();
        boolean interrupted=Thread.interrupted();
        try {
          child.waitFor(3,TimeUnit.SECONDS);
          for(var descendant:descendants) if(descendant.isAlive()) try { descendant.onExit().get(1,TimeUnit.SECONDS); } catch(ExecutionException|TimeoutException ignored) {}
        } catch(InterruptedException e) { interrupted=true; }
        finally { if(interrupted) Thread.currentThread().interrupt(); }
      }
      io.shutdownNow();
      if(scratch!=null) removeOwnedDirectory(scratch);
    }
  }
  private static FoliException failed() { return new FoliException(HttpStatus.UNPROCESSABLE_CONTENT,"READER_RESOURCE_LIMIT","The isolated reader failed or exceeded its resource budget. No complete review was produced."); }
  private static String quoteArg(String value) { return "\""+value.replace("\\","\\\\").replace("\"","\\\"")+"\""; }
  private static void removeOwnedDirectory(Path directory) {
    // Only this invocation's freshly created directory, without following symbolic links.
    try(var paths=Files.walk(directory)) { paths.sorted(Comparator.reverseOrder()).forEach(p -> { try { Files.deleteIfExists(p); } catch(IOException ignored) {} }); }
    catch(IOException ignored) {}
  }
  private static class LimitedInputStream extends FilterInputStream {
    private int remaining=MAX_OUTPUT;
    LimitedInputStream(InputStream input) { super(input); }
    @Override public int read() throws IOException { int b=super.read(); if(b>=0 && --remaining<0) throw new IOException("Reader output limit"); return b; }
    @Override public int read(byte[] bytes,int offset,int length) throws IOException {
      if(remaining<=0) throw new IOException("Reader output limit");
      int n=super.read(bytes,offset,Math.min(length,remaining)); if(n>0) remaining-=n; return n;
    }
  }
}
