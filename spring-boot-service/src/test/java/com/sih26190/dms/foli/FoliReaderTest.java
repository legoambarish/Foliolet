package com.sih26190.dms.foli;

import java.nio.file.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Real bounded child JVMs, rather than mocked parser behavior. */
class FoliReaderTest {
  @TempDir Path directory;
  FoliProperties config() { var c=new FoliProperties(); c.setTempDir(directory.toString()); return c; }
  void clean() throws Exception { try(var files=Files.list(directory)) { assertEquals(0,files.count(),"Per-job OCR and JVM scratch must be removed"); } }
  @Test void isolatedReaderAccountsFor125PagesAndRendersOriginal() throws Exception {
    var reader=new FoliReader(config()); var source=FoliReadingTest.source(FoliReadingTest.pdf(125),"pdf");
    var snapshot=reader.extract(source,p -> {});
    assertEquals(125,snapshot.manifest().readablePages()); assertTrue(snapshot.pages().get(124).text().contains("Notwithstanding"));
    byte[] png=reader.renderPage(source,125); assertEquals(0x89,png[0]&0xff); assertEquals('P',png[1]); clean();
  }
  @Test void isolatedCorruptInputReturnsSafeErrorWithoutLeavingScratch() throws Exception {
    var failure=assertThrows(FoliException.class,() -> new FoliReader(config()).extract(FoliReadingTest.source(new byte[]{1,2,3},"pdf"),p -> {}));
    assertEquals("CORRUPT_SOURCE",failure.code()); clean();
  }
  @Test void cancellationTerminatesTheReaderAndCleansScratch() throws Exception {
    var reader=new FoliReader(config()); var source=FoliReadingTest.source(FoliReadingTest.pdf(200),"pdf");
    var executor=Executors.newSingleThreadExecutor(); var started=new CountDownLatch(1);
    var task=executor.submit(() -> reader.extract(source,p -> { started.countDown(); try { Thread.sleep(10000); } catch(InterruptedException e) { Thread.currentThread().interrupt(); } }));
    try {
      assertTrue(started.await(15,TimeUnit.SECONDS)); assertTrue(task.cancel(true));
    } finally { executor.shutdownNow(); assertTrue(executor.awaitTermination(8,TimeUnit.SECONDS)); }
    clean();
  }
  @Test void aBlockedProgressConsumerCannotDefeatTheChildWallBudget() throws Exception {
    // The child writes enough progress/output to fill its pipe; the parent still enforces the deadline.
    var c=config(); c.setExtractionTimeoutSeconds(1); var reader=new FoliReader(c);
    var source=FoliReadingTest.source(FoliReadingTest.pdf(200),"pdf");
    var failure=assertThrows(FoliException.class,() -> reader.extract(source,p -> { try { Thread.sleep(4000); } catch(InterruptedException e) { Thread.currentThread().interrupt(); } }));
    assertTrue(java.util.Set.of("READER_TIMEOUT","READER_RESOURCE_LIMIT").contains(failure.code())); clean();
  }
}
