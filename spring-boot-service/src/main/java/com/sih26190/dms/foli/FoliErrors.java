package com.sih26190.dms.foli;

import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestControllerAdvice(basePackages = "com.sih26190.dms.foli")
public class FoliErrors {
  @ExceptionHandler(FoliException.class)
  public ResponseEntity<?> known(FoliException e) {
    return ResponseEntity.status(e.getStatusCode()).body(Map.of("code",e.code(),"message",e.getReason()));
  }
  @ExceptionHandler({IllegalArgumentException.class,
      org.springframework.web.bind.MethodArgumentNotValidException.class,
      org.springframework.http.converter.HttpMessageNotReadableException.class,
      org.springframework.web.bind.MissingServletRequestParameterException.class})
  public ResponseEntity<?> invalid(Exception e) {
    return ResponseEntity.badRequest().body(Map.of("code","INVALID_REQUEST","message","Check the request fields and limits."));
  }
  @ExceptionHandler(Exception.class)
  public ResponseEntity<?> failure(Exception e) {
    // Do not serialize/log exception messages that may contain private model/source data.
    return ResponseEntity.status(503).body(Map.of("code","UNAVAILABLE","message","Foli could not complete this request. Retry or review the original."));
  }
}
