package com.sih26190.dms.intake;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sih26190.dms.foli.*;
import com.sih26190.dms.selective.ClaimCanonicalizer;
import java.nio.file.*;
import java.util.Map;
import static org.mockito.Mockito.mock;

/** Replays an immutable, local benchmark snapshot without OCR or any model/network calls. */
public final class IntakeReextractMain {
  public static void main(String[] args) throws Exception {
    var json=new ObjectMapper();var source=json.readTree(Path.of(args[0]).toFile());
    var snapshot=json.treeToValue(source.path("snapshot"),FoliData.Snapshot.class);
    var facts=new FactSuggestions(new ClaimCanonicalizer(),new CitationVerifier(),mock(FoliLocalModel.class));
    var result=facts.suggest(snapshot,ignored -> {});
    json.writeValue(Path.of(args[1]).toFile(),Map.of("result",result,"sameSnapshot",true,"networkCalls",0));
    System.out.println("REPLAY_COMPLETE fields="+result.fields().size()+" modelCalls="+result.diagnostics().get("modelCalls"));
  }
}
