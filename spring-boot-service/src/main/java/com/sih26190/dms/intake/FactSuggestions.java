package com.sih26190.dms.intake;

import com.fasterxml.jackson.databind.*;
import com.sih26190.dms.foli.*;
import com.sih26190.dms.foli.FoliData.*;
import com.sih26190.dms.foli.FoliRetrievalService.Span;
import com.sih26190.dms.selective.*;
import com.sih26190.dms.selective.WalletDtos.ClaimInput;
import java.text.Normalizer;
import java.util.*;
import java.util.function.Consumer;
import java.util.regex.*;
import org.springframework.stereotype.Service;

/** Positioned source evidence binds each fact; local models may only select existing cell IDs. */
@Service
public class FactSuggestions {
  public static final String VERSION="intake-facts-3-labels-tables";
  public record Fragment(String layer,int start,int end,String quote,double left,double top,double width,double height,double confidence,
                         String channel,String method,int rotation) {}
  public record Support(String id,String quality,String relationship,List<Fragment> labels,List<Fragment> values,List<Fragment> headers,
                        List<String> reasons,String normalization,List<Fragment> alternatives) {}
  public record Candidate(String path,String label,String type,String value,String evidence,Citation citation,Support support) {
    public Candidate(String path,String label,String type,String value,String evidence,Citation citation) {this(path,label,type,value,evidence,citation,null);}
    public ClaimInput claim() { return new ClaimInput(path,label,type,value); }
  }
  public record Result(List<Candidate> fields,int discarded,boolean partial,List<String> warnings,Map<String,Object> diagnostics) {
    public Result(List<Candidate> fields,int discarded,boolean partial,List<String> warnings) {this(fields,discarded,partial,warnings,Map.of());}
  }
  private static final Pattern LINE=Pattern.compile("(?m)^([^\\r\\n]{1,100}?)\\s*[:=]\\s*([^\\r\\n]{1,1000})$");
  private final ClaimCanonicalizer canonical;
  private final CitationVerifier citations;
  private final FoliLocalModel model;
  private final ObjectMapper json=new ObjectMapper();
  public FactSuggestions(ClaimCanonicalizer canonical,CitationVerifier citations,FoliLocalModel model) {
    this.canonical=canonical; this.citations=citations; this.model=model;
  }
  public Result suggest(Snapshot snapshot,Consumer<String> progress) {
    return new LayoutFacts(canonical,citations).extract(snapshot,progress,model);
  }
  /** Conservative compatibility parser for saved v1 model proposals; new intake uses LayoutFacts. */
  public Result parse(String output,Snapshot snapshot) {
    if(output==null || output.length()>64_000) throw new IllegalArgumentException("Invalid local proposal");
    JsonNode array;
    try { array=json.readTree(output).path("fields"); }
    catch(Exception e) { throw new IllegalArgumentException("The local proposal was not valid JSON"); }
    if(!array.isArray() || array.size()>80) throw new IllegalArgumentException("Invalid proposal list");
    var fields=new TreeMap<String,Candidate>(); int discarded=0;
    for(var node:array) {
      Candidate field=validate(node,snapshot);
      if(field==null || fields.size()>=40 || fields.putIfAbsent(field.path(),field)!=null) discarded++;
    }
    return new Result(List.copyOf(fields.values()),discarded,false,List.of());
  }
  private Candidate validate(JsonNode node,Snapshot snapshot) {
    try {
      if(!node.isObject() || !node.path("page").isIntegralNumber()) return null;
      int number=node.path("page").intValue();
      if(number<1 || number>snapshot.pages().size()) return null;
      var page=snapshot.pages().get(number-1);
      if(!Set.of("TEXT","OCR","MIXED_OCR").contains(page.status()) || page.warnings().stream().anyMatch(w -> w.contains("columns"))) return null;
      String evidence=text(node,"evidence");
      if(evidence.length()>1200 || evidence.isBlank() || evidence.contains("\n") || evidence.contains("\r")) return null;
      int start=page.text().indexOf(evidence);
      if(start<0 || (start>0 && page.text().charAt(start-1)!='\n' && page.text().charAt(start-1)!='\r')
          || start+evidence.length()<page.text().length() && "\r\n".indexOf(page.text().charAt(start+evidence.length()))<0) return null;
      var matched=LINE.matcher(evidence);
      if(!matched.matches()) return null;
      String label=canonical.text(matched.group(1),100), literal=matched.group(2).strip();
      if(!label.equals(canonical.text(text(node,"label"),100))) return null;
      int confidenceStart=start,confidenceEnd=start+evidence.length();
      boolean mixed=page.status().equals("MIXED_OCR");
      if(mixed) {
        int marker=page.text().indexOf("\n[Rendered-page OCR transcription]\n");
        if(page.words().isEmpty()) return null;
        if(marker>=0) {
          if(start>=marker) return null; // Image-only extra fields need separate human review.
          int offset=marker+"\n[Rendered-page OCR transcription]\n".length();
          var rendered=LINE.matcher(page.text().substring(offset)); boolean corroborated=false;
          while(rendered.find()) if(label.equals(canonical.text(rendered.group(1),100))
              && canonical.text(literal,1000).equals(canonical.text(rendered.group(2),1000))) {
            confidenceStart=offset+rendered.start();confidenceEnd=offset+rendered.end();corroborated=true;break;
          }
          if(!corroborated) return null;
        }
      }
      String type=text(node,"type");
      // The local model sometimes emits numeric marks as text. Only explicit
      // score labels with an entire plain numeric RHS get this deterministic
      // type correction; identifiers and units retain their literal semantics.
      if(type.equals("string") && label.matches("(?i)(?:math|mathematics|science|physics|chemistry|biology|english|history|geography|cgpa)(?: marks| score)?")
          && literal.matches("-?[0-9]+(?:\\.[0-9]+)?%?")) type="decimal";
      String proposed=node.path("value").isNumber() && type.equals("decimal")?node.path("value").asText():text(node,"value");
      String value=canonical.value(type,proposed);
      String supported; boolean percentage=false;
      if(type.equals("decimal")) {
        // Entire adjacent value, not a substring of 190, -90, 90/100, O0, a range or another column.
        String raw=literal;
        boolean percent=raw.endsWith("%"); percentage=percent;
        if(percent) raw=raw.substring(0,raw.length()-1).strip();
        if(raw.matches("-?[0-9]{1,3}(?:,[0-9]{3})+(?:\\.[0-9]+)?")) raw=raw.replace(",","");
        supported=canonical.value(type,raw);
        if(percent) label=canonical.text(label+" (%)",100);
      } else supported=canonical.value(type,literal);
      if(!value.equals(supported)) return null;
      final int from=confidenceStart,to=confidenceEnd;
      if(page.ocr() && (page.confidence()==null || page.confidence()<85 || page.words().stream()
          .anyMatch(w -> w.end()>from && w.start()<to && w.confidence()<80))) return null;
      String path=path(label)+(percentage?"_percent":"");
      if(path.equals("education.cgpa") && (!type.equals("decimal") || new java.math.BigDecimal(value).signum()<0 || new java.math.BigDecimal(value).compareTo(java.math.BigDecimal.TEN)>0)) return null;
      var citation=citations.verify(snapshot,new Span("F"+number+"_"+start,number,start,start+evidence.length(),evidence),evidence);
      if(citation.isEmpty()) return null;
      var verified=citation.get();
      if(mixed) verified=new Citation(verified.id(),verified.documentId(),verified.sourceHash(),verified.version(),verified.page(),verified.start(),verified.end(),verified.quote(),"Embedded text corroborated by OCR",true,verified.warnings());
      return new Candidate(path,label,type,value,evidence,verified);
    } catch(RuntimeException e) { return null; }
  }
  private static String text(JsonNode node,String key) {
    if(!node.path(key).isTextual()) throw new IllegalArgumentException();
    return node.path(key).textValue();
  }
  public static String path(String label) {
    String slug=Normalizer.normalize(label,Normalizer.Form.NFD).replaceAll("[^\\p{ASCII}]","")
        .toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+","_").replaceAll("^_+|_+$","");
    return switch(slug) {
      case "math","mathematics","math_marks","mathematics_marks" -> "education.math";
      case "cgpa" -> "education.cgpa";
      case "name","full_name" -> "person.name";
      case "institution" -> "education.institution";
      case "course" -> "education.course";
      case "date_of_birth" -> "person.birth_date";
      case "purchase_date" -> "purchase.date";
      case "product_identifier" -> "purchase.product_id";
      default -> { if(slug.isEmpty() || !Character.isLetter(slug.charAt(0))) throw new IllegalArgumentException();
        yield "extracted."+slug.substring(0,Math.min(60,slug.length())); }
    };
  }
}
