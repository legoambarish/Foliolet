package com.sih26190.dms.foli;

import java.util.*;
import java.util.regex.*;
import org.springframework.stereotype.Service;
import static com.sih26190.dms.foli.FoliData.*;
import static com.sih26190.dms.foli.FoliRetrievalService.Span;

@Service
public class CitationVerifier {
  public Optional<Citation> verify(Snapshot snapshot, Span span, String requestedQuote) {
    if (span.page()<1 || span.page()>snapshot.pages().size()) return Optional.empty();
    var page=snapshot.pages().get(span.page()-1);
    if (span.start()<0 || span.end()>page.text().length() || span.end()<span.start()
        || !page.text().substring(span.start(),span.end()).equals(span.text())) return Optional.empty();
    String quote=requestedQuote==null || requestedQuote.isBlank()?span.text():requestedQuote;
    int within=span.text().indexOf(quote); if (within<0 || quote.isBlank()) return Optional.empty();
    int start=span.start()+within, end=start+quote.length();
    if (!page.text().substring(start,end).equals(quote)) return Optional.empty();
    return Optional.of(new Citation(span.id(),snapshot.document().id(),snapshot.hash(),snapshot.document().version(),
        page.number(),start,end,quote,page.ocr()?"OCR transcription":page.status().equals("TEXT")?"Embedded source text":"Uncertain source text",
        true,page.warnings()));
  }

  /** A model-written quotation is never labeled verified by string cleanup. */
  public String suppressUnsupportedQuotes(String answer, List<Span> permitted, List<String> warnings) {
    var quote=Pattern.compile("[\"“]([^\"”\\n]{2,1500})[\"”]").matcher(answer);
    var output=new StringBuffer();
    while(quote.find()) {
      String words=quote.group(1);
      if (permitted.stream().noneMatch(s -> s.text().contains(words))) {
        quote.appendReplacement(output,Matcher.quoteReplacement("[unsupported quotation omitted]"));
        warnings.add("A model-written quotation did not match the selected source and was omitted.");
      } else quote.appendReplacement(output,Matcher.quoteReplacement(quote.group()));
    }
    quote.appendTail(output); return output.toString();
  }
}
