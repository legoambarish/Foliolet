package com.sih26190.dms.foli;

import java.util.*;
import java.util.regex.Pattern;
import static com.sih26190.dms.foli.FoliData.*;

/** A narrow quote-only path for inspecting instruction-like source lines.
 * This never decides whether an ordinary document question is allowed. */
final class FoliSourceInstructions {
  private FoliSourceInstructions() {}
  private static final Pattern INSPECTION = Pattern.compile(
      "(?i)\\b(?:quote|identify|show|find|what|which|explain|analy[sz]e)\\b");
  private static final Pattern SUBJECT = Pattern.compile(
      "(?i)\\b(?:(?:suspicious|embedded|malicious)\\s+(?:instructions?|commands?|prompts?)|prompt\\s+injection|(?:fake\\s+)?(?:system|developer|assistant)\\s+(?:messages?|instructions?|prompts?))\\b");
  private static final Pattern SOURCE_LINE = Pattern.compile(
      "(?im)^[\\t ]*(?:(?:system|developer|assistant)\\s*:.*|[^\\r\\n]*\\b(?:ignore|disregard|override)\\s+(?:all\\s+)?(?:previous|prior|earlier|system)\\s+instructions?[^\\r\\n]*)$");

  static Optional<FoliChatService.Answer> inspect(String question,Snapshot snapshot,CitationVerifier verifier) {
    if (!INSPECTION.matcher(question).find() || !SUBJECT.matcher(question).find()) return Optional.empty();
    var citations=new ArrayList<Citation>(); var text=new StringBuilder(
        "These source lines look like instructions addressed to an assistant. Quoted as document text:\n");
    int characters=0;
    for(var page:snapshot.pages()) {
      var lines=SOURCE_LINE.matcher(page.text());
      while(lines.find() && citations.size()<4) {
        if(lines.group().length()>1500 || characters+lines.group().length()>3000) continue;
        String id="E"+(citations.size()+1);
        var span=new FoliRetrievalService.Span(id,page.number(),lines.start(),lines.end(),lines.group());
        var citation=verifier.verify(snapshot,span,null);
        if(citation.isEmpty()) continue;
        citations.add(citation.get()); characters+=lines.group().length();
        text.append("\n\"").append(lines.group()).append("\" [").append(id).append("]\n");
      }
      if(citations.size()==4) break;
    }
    if(citations.isEmpty()) return Optional.empty();
    text.append("\nThese lines do not control my behavior. This is a limited pattern check, not an exhaustive security review.");
    return Optional.of(new FoliChatService.Answer(text.toString(),"INTERPRETATION",List.copyOf(citations),snapshot.manifest(),
        snapshot.manifest().warnings(),List.of(),Map.of("mode","instruction-quotes"),Map.of()));
  }
}
