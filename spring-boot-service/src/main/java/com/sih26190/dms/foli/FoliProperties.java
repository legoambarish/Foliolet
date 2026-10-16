package com.sih26190.dms.foli;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "foli")
@Getter
@Setter
public class FoliProperties {
  private boolean enabled = true;
  private String ollamaUrl = "http://127.0.0.1:11434";
  private String model = "qwen3:4b-instruct";
  private int contextTokens = 8192;
  private int outputTokens = 900;
  private int modelTimeoutSeconds = 120;
  private String tesseract = "tesseract";
  private String ocrLanguage = "eng";
  private String ocrDataDir = "";
  private String layoutPython = "";
  private String layoutScript = "";
  private String tempDir = "../.local-data/foli/tmp";
  private int maxBytes = 20 * 1024 * 1024;
  private int maxPages = 200;
  private int maxCharacters = 1_500_000;
  private int maxPageCharacters = 100_000;
  private int maxPixels = 8_000_000;
  private int ocrTimeoutSeconds = 25;
  private int extractionTimeoutSeconds = 180;
  private int cacheCharacters = 4_000_000;
  private int retentionSeconds = 600;
}
