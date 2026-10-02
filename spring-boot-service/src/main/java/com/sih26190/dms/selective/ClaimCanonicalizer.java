package com.sih26190.dms.selective;

import java.math.BigDecimal;
import java.text.Normalizer;
import java.time.LocalDate;
import org.springframework.stereotype.Component;

@Component
public class ClaimCanonicalizer {
  public String text(String value, int limit) {
    if (value == null) throw new IllegalArgumentException("A value is required");
    if (value.codePoints().anyMatch(Character::isISOControl))
      throw new IllegalArgumentException("Control characters are not allowed");
    String result = Normalizer.normalize(value.strip(), Normalizer.Form.NFC);
    if (result.isEmpty()
        || result.length() > limit
        || result.codePoints().anyMatch(Character::isISOControl))
      throw new IllegalArgumentException("Invalid or overlong text");
    return result;
  }

  public String path(String path) {
    String result = text(path, 100);
    if (!result.matches("[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)*"))
      throw new IllegalArgumentException(
          "Fact paths use lowercase letters, numbers, underscores and dots");
    return result;
  }

  public String value(String type, String value) {
    String normalized = text(value, 1000);
    return switch (type) {
      case "string" -> normalized;
      case "decimal" -> {
        if (!normalized.matches("-?[0-9]{1,30}(\\.[0-9]{1,12})?"))
          throw new IllegalArgumentException("Use a plain decimal without units or exponents");
        yield new BigDecimal(normalized).stripTrailingZeros().toPlainString();
      }
      case "boolean" -> {
        if (!normalized.equalsIgnoreCase("true") && !normalized.equalsIgnoreCase("false"))
          throw new IllegalArgumentException("Boolean facts must be true or false");
        yield normalized.toLowerCase(java.util.Locale.ROOT);
      }
      case "date" -> {
        if (!normalized.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}"))
          throw new IllegalArgumentException("Dates must use YYYY-MM-DD");
        yield LocalDate.parse(normalized).toString();
      }
      default -> throw new IllegalArgumentException("Unsupported fact type");
    };
  }
}
