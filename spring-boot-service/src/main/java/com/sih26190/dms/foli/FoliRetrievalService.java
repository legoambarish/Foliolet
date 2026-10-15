package com.sih26190.dms.foli;

import java.util.*;
import java.util.regex.*;
import org.springframework.stereotype.Service;
import static com.sih26190.dms.foli.FoliData.*;

@Service
public class FoliRetrievalService {
  public record Span(String id, int page, int start, int end, String text) {}
  private static final Set<String> STOP=Set.of("the","a","an","of","to","is","it","and","in","on","for","what","how","does","this","that","document","please","me","can","you","are","be","with","as","my",
      "do","did","when","who","which","where","why","would","could","should","need","will","has","have","was","were","am");
  private static final Map<String,String> EXPANSIONS=Map.ofEntries(
      Map.entry("cancel","cancellation terminate termination notice"),Map.entry("continue","renewal renew subscription"),
      Map.entry("compensation","liability damages loss cap"),Map.entry("quality","warranty warranties defect"),
      Map.entry("information","data privacy retention shared"),Map.entry("unused","dormant account charge"),
      Map.entry("price","fee fees charge tariff amount"),Map.entry("court","arbitration jurisdiction dispute"),
      Map.entry("own","unilateral discretion variation"),Map.entry("promises","warranty warranties guarantee"),
      Map.entry("dispute","disputes arbitration seated jurisdiction binding"),
      Map.entry("email","cancellation registered post notice schedule"));

  public List<Span> all(Snapshot snapshot) {
    var result=new ArrayList<Span>(); int serial=1;
    for (var page:snapshot.pages()) {
      String text=page.text(); int start=0;
      while (start<text.length()) {
        int end=Math.min(text.length(),start+1400);
        if (end<text.length()) {
          int boundary=text.lastIndexOf('\n',end);
          if (boundary>start+500) end=boundary+1;
        }
        if (!text.substring(start,end).isBlank()) result.add(new Span("E"+serial++,page.number(),start,end,text.substring(start,end)));
        if (end==text.length()) break;
        start=Math.max(start+1,end-160);
      }
    }
    return result;
  }

  public List<Span> retrieve(Snapshot snapshot, String question) {
    List<Span> spans=all(snapshot);
    if (snapshot.manifest().characters()<=10_000) return spans;
    String expanded=question.toLowerCase(Locale.ROOT);
    for (var entry:EXPANSIONS.entrySet()) if (expanded.contains(entry.getKey())) expanded+=" "+entry.getValue();
    var terms=tokens(expanded); var documentFrequency=new HashMap<String,Integer>();
    for (var span:spans) for (var token:tokens(span.text())) documentFrequency.merge(token,1,Integer::sum);
    var quotes=new ArrayList<String>(); var quoted=Pattern.compile("[\"“]([^\"”]{3,500})[\"”]").matcher(question);
    while(quoted.find()) quotes.add(quoted.group(1));
    var scores=new HashMap<Span,Double>();
    for (var span:spans) {
      String lower=span.text().toLowerCase(Locale.ROOT); Set<String> words=tokens(lower); double score=0;
      // BM25-style IDF suppresses repeated page headers/boilerplate. Common
      // auxiliary words must not turn unrelated archive pages into evidence.
      for (var term:terms) if (words.contains(term)) {
        int frequency=documentFrequency.getOrDefault(term,0);
        score+=Math.log(1+(spans.size()-frequency+.5)/(frequency+.5));
      }
      for (String quote:quotes) if (span.text().contains(quote)) score+=50;
      var clause=Pattern.compile("(?i)\\b(?:clause|section|paragraph)\\s+(\\d+)\\b").matcher(question);
      boolean first=true;
      while(clause.find()) {
        String number=clause.group(1);
        if(Pattern.compile("(?im)^\\s*(?:clause|section)\\s+"+number+"[.: ]").matcher(span.text()).find()) score+=first?100:25;
        else if(Pattern.compile("(?i)\\b(?:clause|section)\\s+"+number+"[.: ]").matcher(span.text()).find()) score+=10;
        first=false;
      }
      if (score>0) scores.put(span,score);
    }
    var ranked=new ArrayList<>(scores.keySet());
    ranked.sort(Comparator.<Span>comparingDouble(s -> -scores.get(s)).thenComparingInt(Span::page).thenComparingInt(Span::start));
    var chosen=new LinkedHashSet<Span>(); int characters=0;
    double floor=ranked.isEmpty()?0:scores.get(ranked.get(0))*.10;
    for (var span:ranked) {
      if(scores.get(span)<floor) continue;
      if (chosen.size()>=6 || characters+span.text().length()>10_000) break;
      chosen.add(span); characters+=span.text().length();
    }
    // Follow references from retrieved operative clauses into definitions/schedules.
    String context=chosen.stream().map(Span::text).collect(java.util.stream.Collectors.joining("\n"));
    var references=Pattern.compile("(?i)\\b(clause|section|schedule|appendix)\\s+([A-Z]|\\d+)\\b").matcher(context);
    while(references.find() && chosen.size()<12) {
      var heading=Pattern.compile("(?im)^\\s*(?:Clause \\d+\\. )?"+Pattern.quote(references.group())+"\\b");
      for (var span:spans) if (!chosen.contains(span) && heading.matcher(span.text()).find() && characters+span.text().length()<=14_000) {
        chosen.add(span); characters+=span.text().length(); break;
      }
    }
    return List.copyOf(chosen);
  }

  static Set<String> tokens(String text) {
    var result=new HashSet<String>(); var matcher=Pattern.compile("[\\p{L}\\p{N}]+(?:['’-][\\p{L}\\p{N}]+)?").matcher(text.toLowerCase(Locale.ROOT));
    while(matcher.find()) { String word=matcher.group(); if (word.length()>1 && !STOP.contains(word)) result.add(word); }
    return result;
  }
}
