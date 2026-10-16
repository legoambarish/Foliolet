package com.sih26190.dms.intake;

import com.sih26190.dms.foli.CitationVerifier;
import com.sih26190.dms.foli.FoliData.*;
import com.sih26190.dms.foli.FoliRetrievalService.Span;
import com.sih26190.dms.selective.ClaimCanonicalizer;
import java.util.*;
import java.util.function.Consumer;
import java.util.regex.*;

/** Bounded, local, review-only proposals. Geometry selects cells; exact source
 * offsets bind their text. Neither OCR confidence nor a citation authenticates
 * an issuer or proves transcription accuracy. No arithmetic or OCR repair. */
final class SourceFactRules {
  private static final Pattern LITERAL=Pattern.compile("(?m)^([^\\r\\n]{1,100}?)\\s*[:=]\\s*([^\\r\\n]{1,1000})$");
  private static final Pattern NUMBER=Pattern.compile("-?(?:[0-9]{1,30}|[0-9]{1,3}(?:,[0-9]{3})+)(?:\\.[0-9]{1,12})?%?");
  private static final String MARKS="(?i)(?:math|mathematics|science|physics|chemistry|biology|english|history|geography|cgpa)(?: marks| score)?";
  private static final Set<String> ROW_HEADERS=Set.of("subject","course","module","paper","description","item","field","particulars");
  private static final Set<String> VALUE_HEADERS=Set.of("marks","marks obtained","obtained marks","obtained","score","total marks","result","grade","value","amount","total");
  private static final int MAX_WORDS=20_000,MAX_ROWS=2000,MAX_FIELDS=40,MAX_SPAN=6000;
  private final ClaimCanonicalizer canonical;
  private final CitationVerifier citations;
  private final Map<String,Integer> diagnostics=new TreeMap<>();
  private final List<FactSuggestions.Candidate> proposed=new ArrayList<>();
  private boolean partial;
  private int discarded;
  SourceFactRules(ClaimCanonicalizer canonical,CitationVerifier citations) {this.canonical=canonical;this.citations=citations;}

  FactSuggestions.Result suggest(Snapshot source,Consumer<String> progress) {
    long deadline=System.nanoTime()+java.util.concurrent.TimeUnit.SECONDS.toNanos(10);
    for(var page:source.pages()) {
      if(Thread.currentThread().isInterrupted()) throw new java.util.concurrent.CancellationException();
      if(System.nanoTime()>deadline) {reject("TIME_BUDGET");partial=true;break;}
      count("PAGES_ACCOUNTED"); progress.accept("Matching source facts · page "+page.number()+" of "+source.pages().size());
      if(page.status().equals("MIXED_OCR") && page.text().contains("\n[Rendered-page OCR transcription]\n")) {
        mixedLiterals(source,page); continue;
      }
      if(!Set.of("TEXT","OCR","OCR_UNCERTAIN","MIXED_OCR").contains(page.status())) {
        // A contradictory hidden/native layer must not be resolved by guessing.
        // The pre-existing corroboration validator remains available separately.
        reject(page.status().equals("MIXED_OCR")?"MIXED_LAYER_REVIEW":"PAGE_NOT_READABLE"); continue;
      }
      if(page.words().size()>MAX_WORDS) {reject("WORD_BUDGET");partial=true;continue;}
      var words=page.words();
      if(words.stream().anyMatch(w -> !validWord(page,w))) {reject("INVALID_SOURCE_GEOMETRY");continue;}
      boolean geometryRequired=page.ocr() || page.warnings().stream().anyMatch(w -> w.toLowerCase(Locale.ROOT).contains("columns"));
      var literalRegions=new ArrayList<int[]>();
      var matcher=LITERAL.matcher(page.text());
      while(matcher.find()) {
        if(System.nanoTime()>deadline) {reject("TIME_BUDGET");partial=true;break;}
        count("LITERAL_ROWS_SEEN");
        literalRegions.add(new int[]{matcher.start(),matcher.end()});
        var relevant=within(words,matcher.start(),matcher.end());
        if(geometryRequired && (relevant.isEmpty() || !sameRow(relevant) || !covered(page.text(),matcher.start(),matcher.end(),relevant))) {
          reject("LITERAL_GEOMETRY_MISMATCH");continue;
        }
        offer(source,page,matcher.group(1),matcher.group(2),matcher.start(),matcher.end(),relevant,false);
      }
      if(words.isEmpty()) {if(geometryRequired) reject("NO_WORD_GEOMETRY");continue;}
      var rows=rows(words); List<Cell> header=null; int headerAt=-1; double lastTop=-1;
      for(int i=0;i<rows.size();i++) {
        if(i>=MAX_ROWS || System.nanoTime()>deadline) {reject("ROW_BUDGET");partial=true;break;}
        var row=rows.get(i); count("GEOMETRY_ROWS_SEEN");
        if(lastTop>=0 && top(row)-lastTop>height(row)*8) header=null;
        lastTop=top(row);
        var cells=cells(row); if(cells.isEmpty()) {reject("OVERLAPPING_CELLS");header=null;continue;}
        int begin=row.stream().mapToInt(Word::start).min().orElse(0),end=row.stream().mapToInt(Word::end).max().orElse(0);
        if(literalRegions.stream().anyMatch(s -> s[0]<end && begin<s[1])) continue;
        if(cells.size()<2) continue;
        String first=normalize(cells.get(0).text());
        if(ROW_HEADERS.contains(first)) {
          header=cells;headerAt=begin;count("HEADERS_SEEN");continue;
        }
        if(header!=null && header.size()==cells.size()) {
          int selected=-1;
          for(int j=1;j<header.size();j++) if(VALUE_HEADERS.contains(normalize(header.get(j).text()))) {
            if(selected!=-1) {selected=-2;break;} selected=j;
          }
          if(selected<1) {reject("AMBIGUOUS_VALUE_HEADER");continue;}
          if(!aligned(header,cells)) {reject("COLUMN_ALIGNMENT_MISMATCH");continue;}
          var evidenceWords=new ArrayList<Word>();
          evidenceWords.addAll(header.get(0).words());evidenceWords.addAll(header.get(selected).words());
          evidenceWords.addAll(cells.get(0).words());evidenceWords.addAll(cells.get(selected).words());
          String label=cells.get(0).text()+" — "+header.get(selected).text();
          offer(source,page,label,cells.get(selected).text(),Math.min(headerAt,begin),end,evidenceWords,true);
        } else if(cells.size()==2 && header==null) {
          String label=cells.get(0).text().replaceFirst("\\s*[:=]$","");
          if(!directLabel(label)) {count("UNSUPPORTED_ROWS");continue;}
          offer(source,page,label,cells.get(1).text(),begin,end,row,false);
        } else {reject("MISSING_OR_MISMATCHED_HEADER");}
      }
    }
    // Identical model/source duplicates are harmless; repeated labels at distinct
    // locations may describe different terms/people/semesters, even with equal values.
    var unique=new TreeMap<String,FactSuggestions.Candidate>();var ambiguous=new HashSet<String>();
    for(var field:proposed) {
      if(ambiguous.contains(field.path())) {reject("DUPLICATE_SCOPE");continue;}
      var old=unique.get(field.path());
      if(old==null) unique.put(field.path(),field);
      else if(old.equals(field)) count("REDUNDANT_PROPOSAL");
      else {unique.remove(field.path());ambiguous.add(field.path());reject("DUPLICATE_SCOPE");reject("DUPLICATE_SCOPE");}
    }
    if(unique.size()>MAX_FIELDS) {partial=true;count("FIELD_BUDGET");}
    var accepted=unique.values().stream().limit(MAX_FIELDS).toList();
    var warnings=new ArrayList<String>();
    if(accepted.isEmpty()) warnings.add("No safely associated source facts were proposed. Check the reasons below, view the original, or enter facts manually. Ask Foli remains available separately.");
    if(accepted.stream().anyMatch(f -> f.citation().provenance().contains("OCR")))
      warnings.add("OCR proposals need visual review: even high-confidence OCR can change digits. Nothing is automatically confirmed or issuer-verified.");
    if(discarded>0) warnings.add("Some rows were withheld rather than guessed. Rejection counts explain ambiguous columns, repeated labels, uncertain words or conflicting document layers.");
    if(partial) warnings.add("The bounded source-matching budget was reached. Missing fields must not be interpreted as absent from the document.");
    diagnostics.put("PROPOSALS_RETURNED",accepted.size());
    return new FactSuggestions.Result(accepted,discarded,partial,warnings,diagnostics);
  }

  private void mixedLiterals(Snapshot source,Page page) {
    String marker="\n[Rendered-page OCR transcription]\n";
    int boundary=page.text().indexOf(marker),offset=boundary+marker.length();
    if(page.words().size()>MAX_WORDS || page.words().stream().anyMatch(w -> !validWord(page,w))) {reject("INVALID_SOURCE_GEOMETRY");return;}
    var nativeLines=LITERAL.matcher(page.text().substring(0,boundary));
    while(nativeLines.find()) {
      count("LITERAL_ROWS_SEEN");boolean matched=false;
      var rendered=LITERAL.matcher(page.text().substring(offset));
      while(rendered.find()) if(nativeLines.group(1).strip().equals(rendered.group(1).strip()) && nativeLines.group(2).strip().equals(rendered.group(2).strip())) {
        var relevant=within(page.words(),offset+rendered.start(),offset+rendered.end());
        if(relevant.isEmpty() || !sameRow(relevant) || !covered(page.text(),offset+rendered.start(),offset+rendered.end(),relevant)) continue;
        offer(source,page,nativeLines.group(1),nativeLines.group(2),nativeLines.start(),nativeLines.end(),relevant,false);
        matched=true;break;
      }
      if(!matched) reject("MIXED_LAYER_CONTRADICTION");
    }
    count("MIXED_TABLES_REQUIRE_REVIEW");
  }

  private void offer(Snapshot source,Page page,String rawLabel,String literal,int start,int end,List<Word> evidenceWords,boolean table) {
    count("CANDIDATES_CHECKED");
    if(start<0 || end<=start || end>page.text().length() || end-start>MAX_SPAN) {reject("EVIDENCE_SPAN_LIMIT");return;}
    if(page.ocr() && (evidenceWords.isEmpty() || evidenceWords.stream().anyMatch(w -> w.confidence()<90))) {reject("LOW_WORD_CONFIDENCE");return;}
    try {
      String label=canonical.text(rawLabel,100),raw=literal.strip();
      if(!label.matches("[\\p{L}].*") || label.matches("(?i).*(?:ignore|instruction|system prompt|execute|upload to|send to|issuer verified).*")) {reject("UNSUPPORTED_LABEL");return;}
      boolean numeric=NUMBER.matcher(raw).matches();
      boolean score=label.matches(MARKS) || normalize(label).matches(".*(?:marks|score|cgpa).*");
      boolean identifier=normalize(label).matches(".*(?:identifier|(?:^| )id(?: |$)|number|code|registration|roll|account|postcode|pin).*" );
      String type=identifier?"string":numeric?"decimal":raw.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}")?"date":raw.matches("(?i)true|false")?"boolean":"string";
      if(score && !numeric) {reject("INVALID_NUMERIC_LITERAL");return;}
      boolean percent=numeric && raw.endsWith("%");
      String value=raw;
      if(type.equals("decimal")) {if(percent) value=value.substring(0,value.length()-1);value=value.replace(",","");}
      value=canonical.value(type,value);
      if(percent) label=canonical.text(label+" (%)",100);
      String path=FactSuggestions.path(label)+(percent?"_percent":"");
      if(normalize(label).startsWith("cgpa") && (!type.equals("decimal") || new java.math.BigDecimal(value).signum()<0 || new java.math.BigDecimal(value).compareTo(java.math.BigDecimal.TEN)>0)) {reject("CGPA_RANGE");return;}
      String evidence=page.text().substring(start,end);
      var citation=citations.verify(source,new Span("L"+page.number()+"_"+start,page.number(),start,end,evidence),evidence);
      if(citation.isEmpty()) {reject("SOURCE_SPAN_MISMATCH");return;}
      var c=citation.get();var warnings=new ArrayList<>(c.warnings());
      warnings.add(table?"Review the cited header and row together; the value was copied, not calculated.":"Review this proposed fact against the original before confirming.");
      if(page.ocr()) warnings.add("Exact OCR text is not proof of exact original digits. Human review is required.");
      c=new Citation(c.id(),c.documentId(),c.sourceHash(),c.version(),c.page(),c.start(),c.end(),c.quote(),
          page.ocr()?"OCR transcription — review required":"Embedded source text — review required",c.sourceVerified(),List.copyOf(warnings));
      proposed.add(new FactSuggestions.Candidate(path,label,type,value,evidence,c));
    } catch(IllegalArgumentException | java.time.DateTimeException e) {reject("INVALID_LITERAL_OR_TYPE");}
  }

  private static boolean validWord(Page page,Word w) {
    return w!=null && w.text()!=null && w.start()>=0 && w.end()>w.start() && w.end()<=page.text().length()
      && page.text().substring(w.start(),w.end()).equals(w.text()) && w.left()>=0 && w.top()>=0 && w.width()>0 && w.height()>0
      && (long)w.left()+w.width()<=1_000_000 && (long)w.top()+w.height()<=1_000_000
      && Double.isFinite(w.confidence()) && w.confidence()>=0 && w.confidence()<=100;
  }
  private static List<Word> within(List<Word> words,int from,int to) {return words.stream().filter(w -> w.start()>=from && w.end()<=to).toList();}
  private static boolean covered(String text,int start,int end,List<Word> words) {
    var bits=new BitSet(end-start);for(var w:words) bits.set(w.start()-start,w.end()-start);
    for(int i=start;i<end;i++) if(!Character.isWhitespace(text.charAt(i)) && !bits.get(i-start)) return false;
    return true;
  }
  private static double center(Word w) {return w.top()+w.height()/2d;}
  private static double height(List<Word> row) {return row.stream().mapToInt(Word::height).sorted().skip(row.size()/2).findFirst().orElse(1);}
  private static double top(List<Word> row) {return row.stream().mapToInt(Word::top).min().orElse(0);}
  private static boolean sameRow(List<Word> row) {
    double mid=row.stream().mapToDouble(SourceFactRules::center).average().orElse(0);
    return row.stream().allMatch(w -> Math.abs(center(w)-mid)<=Math.max(2,height(row)*0.45));
  }
  private static List<List<Word>> rows(List<Word> words) {
    var sorted=words.stream().sorted(Comparator.comparingDouble(SourceFactRules::center).thenComparingInt(Word::left)).toList();
    var rows=new ArrayList<List<Word>>();
    for(var w:sorted) {
      List<Word> row=rows.isEmpty()?null:rows.get(rows.size()-1);
      if(row==null || Math.abs(center(w)-center(row.get(0)))>Math.max(2,Math.min(w.height(),row.get(0).height())*0.45)) {row=new ArrayList<>();rows.add(row);}
      row.add(w);
    }
    rows.forEach(row -> row.sort(Comparator.comparingInt(Word::left)));
    return rows;
  }
  private record Cell(String text,List<Word> words,double left,double right) {double center(){return (left+right)/2;}}
  private static List<Cell> cells(List<Word> row) {
    var result=new ArrayList<Cell>();var group=new ArrayList<Word>();Word previous=null;double h=height(row);
    for(var w:row) {
      if(previous!=null) {
        double gap=w.left()-((long)previous.left()+previous.width());
        if(gap < -Math.min(previous.width(),w.width())*0.35) return List.of();
        if(gap>Math.max(12,h*1.5)) {result.add(cell(group));group=new ArrayList<>();}
      }
      group.add(w);previous=w;
    }
    if(!group.isEmpty()) result.add(cell(group));return result;
  }
  private static Cell cell(List<Word> words) {return new Cell(String.join(" ",words.stream().map(Word::text).toList()),List.copyOf(words),words.get(0).left(),words.stream().mapToLong(w -> (long)w.left()+w.width()).max().orElse(0));}
  private static boolean aligned(List<Cell> header,List<Cell> row) {
    for(int i=0;i<header.size();i++) {
      double left=i==0?Double.NEGATIVE_INFINITY:(header.get(i-1).center()+header.get(i).center())/2;
      double right=i==header.size()-1?Double.POSITIVE_INFINITY:(header.get(i).center()+header.get(i+1).center())/2;
      if(row.get(i).center()<=left || row.get(i).center()>=right) return false;
    }
    return true;
  }
  private static String normalize(String s) {return s.strip().toLowerCase(Locale.ROOT).replaceAll("\\s+"," ").replaceFirst("[:=]$","").strip();}
  private static boolean directLabel(String s) {return s.matches("(?i)(?:name|full name|institution|course|math|mathematics|science|physics|chemistry|biology|english|history|geography|cgpa|total|subtotal|sub total|tax|vat|purchase date|date|date of birth|product identifier|registration number|roll number)(?: marks| score)?");}
  private void count(String reason) {diagnostics.merge(reason,1,Integer::sum);}
  private void reject(String reason) {discarded++;count(reason);}
}
