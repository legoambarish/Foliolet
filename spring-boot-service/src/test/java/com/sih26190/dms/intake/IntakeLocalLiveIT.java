package com.sih26190.dms.intake;

import com.sih26190.dms.foli.*;
import com.sih26190.dms.selective.ClaimCanonicalizer;
import java.util.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static com.sih26190.dms.foli.FoliData.*;

class IntakeLocalLiveIT {
  @Test void realLocalModelProposesLiteralMath90() {
    var config=new FoliProperties();config.setOllamaUrl(System.getenv().getOrDefault("FOLI_OLLAMA_URL",config.getOllamaUrl()));var model=new FoliLocalModel(config);
    assertEquals("READY",model.health().get("status"));
    var source=new Document("wallet:0x"+"a".repeat(64),"Synthetic local test","marks.txt","txt","DRAFT","1",true);
    var page=new Page(1,"Math: 90\nScience: 80\nName: Synthetic Student\nCGPA: unavailable\n","TEXT",null,1,4,0,List.of(),List.of());
    var snapshot=new Snapshot(source,"a".repeat(64),List.of(page),null);
    var facts=new FactSuggestions(new ClaimCanonicalizer(),new CitationVerifier(),model).suggest(snapshot,s -> System.out.println("LIVE_INTAKE "+s));
    System.out.println("SYNTHETIC_INTAKE fields="+facts.fields().stream().map(f -> f.label()+"="+f.value()+" ("+f.type()+")").toList()+" discarded="+facts.discarded());
    assertTrue(facts.fields().stream().anyMatch(f -> f.path().equals("education.math") && f.type().equals("decimal") && f.value().equals("90")));
    assertFalse(facts.fields().stream().anyMatch(f -> f.path().equals("education.cgpa")));
  }
}
