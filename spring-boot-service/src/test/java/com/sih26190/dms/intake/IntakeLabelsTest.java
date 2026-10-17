package com.sih26190.dms.intake;

import com.sih26190.dms.selective.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class IntakeLabelsTest {
  @Test void indicatorsTurnOffAndKeepIncompleteCoverageDistinctFromAbsence() {
    var repository=mock(IntakeRecordRepository.class);var vault=mock(PrivateVault.class);
    var metadata=new IntakeMetadata(repository,vault,new ClaimCanonicalizer());
    var r=new IntakeRecord();r.credentialId="fixture";r.encryptedReport="report";
    when(repository.findById("fixture")).thenReturn(Optional.of(r));
    for(String state:List.of("PASSED","NOT_DETECTED","INCONCLUSIVE")) {
      boolean found=state.equals("PASSED"),complete=!state.equals("INCONCLUSIVE");
      String payload="{\"indicators\":{\"totalPages\":2,\"qrInspectedPages\":"+(complete?2:1)+",\"logoInspectedPages\":"+(complete?2:1)
          +",\"pdfSignature\":\"FAILED\",\"pages\":[{\"logo\":"+found+",\"qr\":"+(found?"[{\"kind\":\"DIGILOCKER_VERIFICATION_ORIGIN\"}]":"[]")+"}]}}";
      when(vault.open("report","intake:fixture:report")).thenReturn(payload);
      var c=metadata.checks(r);assertEquals(state,c.get("branding"));
      assertEquals(state,c.get("qr"));
      assertEquals("FAILED",c.get("pdfSignature"));assertEquals("UNVERIFIED",c.get("issuer"));
    }
    r.encryptedReport=null;
    assertEquals("NOT_CHECKED",metadata.checks(r).get("qr"));
    r.method="WATCHER_ASSISTED";assertEquals("NOT_APPLICABLE",metadata.checks(r).get("imported"));
    r.observationId="observation";r.sessionId="session";assertEquals("PASSED",metadata.checks(r).get("imported"));
    r.method="MANUAL_UPLOAD";assertEquals("NOT_APPLICABLE",metadata.checks(r).get("imported"));
    for(String lineage:List.of("SUGGESTIONS_MODIFIED","SUGGESTIONS_UNMODIFIED","NOT_ASSESSED","STALE_SOURCE")) {
      r.lineage=lineage;
      var stamps=(List<Map<String,String>>)metadata.summary("fixture").get("stamps");
      var modified=stamps.stream().filter(s -> s.get("id").equals("modified")).findFirst().orElseThrow();
      assertEquals(lineage.equals("SUGGESTIONS_MODIFIED")?"MODIFIED":lineage.equals("SUGGESTIONS_UNMODIFIED")?"UNCHANGED":lineage,modified.get("state"));
      assertEquals("UNVERIFIED",stamps.stream().filter(s -> s.get("id").equals("issuer")).findFirst().orElseThrow().get("state"));
    }
  }
}
