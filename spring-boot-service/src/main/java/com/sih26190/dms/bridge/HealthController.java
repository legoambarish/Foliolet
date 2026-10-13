package com.sih26190.dms.bridge;

import java.util.Map;
import org.springframework.web.bind.annotation.*;

@RestController
public class HealthController {
  @GetMapping("/api/public/health")
  public Map<String, String> health() {
    return Map.of("status", "UP", "service", "Foliolet");
  }
}
