package com.sih26190.dms.foli;

import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

public class FoliException extends ResponseStatusException {
  private final String code;
  public FoliException(HttpStatus status, String code, String message) {
    super(status, message); this.code = code;
  }
  public String code() { return code; }
}
