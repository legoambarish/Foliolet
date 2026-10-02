package com.sih26190.dms.selective;

import java.util.Map;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice(basePackages = "com.sih26190.dms.selective")
public class WalletErrors {
  @ExceptionHandler(IllegalArgumentException.class)
  public ResponseEntity<?> invalid(IllegalArgumentException e) {
    return ResponseEntity.badRequest()
        .body(Map.of("message", e.getMessage() == null ? "Invalid request" : e.getMessage()));
  }

  @ExceptionHandler(ResponseStatusException.class)
  public ResponseEntity<?> status(ResponseStatusException e) {
    return ResponseEntity.status(e.getStatusCode())
        .body(Map.of("message", e.getReason() == null ? "Request unavailable" : e.getReason()));
  }

  @ExceptionHandler(org.springframework.web.bind.MethodArgumentNotValidException.class)
  public ResponseEntity<?> validation(Exception e) {
    return ResponseEntity.badRequest()
        .body(Map.of("message", "Required fields or limits are invalid"));
  }
}
