package com.sih26190.dms.selective;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Turns raw model output into candidate facts. The model is untrusted: every candidate must pass
 * the same canonicalizer a typed fact passes, and when the document text is available its quoted
 * evidence must appear verbatim in that text. Nothing here confirms or stores a fact.
 */
public final class FieldScanParser {
  public record ScanField(String path, String label, String type, String value, String evidence) {}

  public record ScanResult(List<ScanField> fields, int discarded) {}

  static final int MAX_FIELDS = 40;
  private static final int MAX_CANDIDATES = 80;
  private static final Set<String> TYPES = Set.of("string", "decimal", "date", "boolean");

  private final ClaimCanonicalizer canonical;
  private final ObjectMapper mapper;

  public FieldScanParser(ClaimCanonicalizer canonical, ObjectMapper mapper) {
    this.canonical = canonical;
    this.mapper = mapper;
  }

  /**
   * @param documentText extracted text used to check evidence, or null when the model read page
   *     images (nothing to compare against, so only canonical validation applies)
   */
  public ScanResult parse(String modelOutput, String documentText) {
    JsonNode root = readJson(modelOutput);
    JsonNode candidates = root.isArray() ? root : root.path("fields");
    if (!candidates.isArray()) throw new IllegalArgumentException("The AI reply had no field list");
    String haystack = documentText == null ? null : flatten(documentText);
    String numericHaystack = haystack == null ? null : haystack.replace(",", "");
    var result = new ArrayList<ScanField>();
    var usedPaths = new HashSet<String>();
    int discarded = 0, seen = 0;
    for (JsonNode node : candidates) {
      if (++seen > MAX_CANDIDATES || result.size() >= MAX_FIELDS) {
        discarded++;
        continue;
      }
      ScanField field = validate(node, haystack, numericHaystack);
      if (field == null || !usedPaths.add(field.path())) discarded++;
      else result.add(field);
    }
    return new ScanResult(List.copyOf(result), discarded);
  }

  private ScanField validate(JsonNode node, String haystack, String numericHaystack) {
    if (!node.isObject()) return null;
    try {
      String type = text(node, "type").toLowerCase(Locale.ROOT);
      if (!TYPES.contains(type)) return null;
      String label = canonical.text(text(node, "label"), 100);
      String value = canonical.value(type, text(node, "value"));
      String path = pathFor(text(node, "path"), label);
      if (path == null || path.endsWith(".cgpa_at_least_8_5")) return null;
      if (path.equals("education.cgpa") && !type.equals("decimal")) return null;
      String evidence = "";
      if (haystack != null) {
        String quoted = flatten(text(node, "evidence"));
        if (quoted.isEmpty() || !haystack.contains(quoted)) return null;
        if (type.equals("string") && !haystack.contains(flatten(value))) return null;
        if (type.equals("decimal") && !quoted.replace(",", "").contains(value)) return null;
        evidence = displayEvidence(text(node, "evidence"));
      }
      return new ScanField(path, label, type, value, evidence);
    } catch (RuntimeException e) {
      return null;
    }
  }

  private String displayEvidence(String raw) {
    String shown = raw.replaceAll("\\s+", " ").strip();
    if (shown.length() > 300) shown = shown.substring(0, 300);
    try {
      return canonical.text(shown, 300);
    } catch (RuntimeException e) {
      return "";
    }
  }

  /** A well-formed model path wins; otherwise derive one from the label under a neutral prefix. */
  private String pathFor(String proposed, String label) {
    try {
      return canonical.path(proposed);
    } catch (RuntimeException ignored) {
    }
    String slug =
        Normalizer.normalize(label, Normalizer.Form.NFD)
            .replaceAll("[^\\p{ASCII}]", "")
            .toLowerCase(Locale.ROOT)
            .replaceAll("[^a-z0-9]+", "_")
            .replaceAll("^_+|_+$", "");
    if (slug.isEmpty() || !Character.isLetter(slug.charAt(0))) return null;
    return "extracted." + slug.substring(0, Math.min(slug.length(), 60));
  }

  private JsonNode readJson(String output) {
    String cleaned = output == null ? "" : output.trim();
    int start = cleaned.indexOf('{'), arrayStart = cleaned.indexOf('[');
    if (arrayStart >= 0 && (start < 0 || arrayStart < start)) start = arrayStart;
    int end = Math.max(cleaned.lastIndexOf('}'), cleaned.lastIndexOf(']'));
    if (start < 0 || end <= start) throw new IllegalArgumentException("The AI reply was not JSON");
    try {
      return mapper.readTree(cleaned.substring(start, end + 1));
    } catch (Exception e) {
      throw new IllegalArgumentException("The AI reply was not valid JSON");
    }
  }

  private static String text(JsonNode node, String field) {
    JsonNode value = node.get(field);
    return value == null || value.isNull() || value.isContainerNode() ? "" : value.asText("");
  }

  /** Case, whitespace and Unicode-form insensitive form used only for containment checks. */
  private static String flatten(String text) {
    return Normalizer.normalize(text, Normalizer.Form.NFC)
        .toLowerCase(Locale.ROOT)
        .replaceAll("\\s+", " ")
        .strip();
  }
}
