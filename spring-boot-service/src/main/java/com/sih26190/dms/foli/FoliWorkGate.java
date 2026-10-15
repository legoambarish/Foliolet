package com.sih26190.dms.foli;

import java.util.concurrent.Semaphore;
import java.util.function.Supplier;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

@Component
public class FoliWorkGate {
  private final Semaphore extraction = new Semaphore(1, true);
  public <T> T reading(Supplier<T> work) {
    if (!extraction.tryAcquire()) throw new FoliException(HttpStatus.TOO_MANY_REQUESTS,
        "BUSY", "Foli is reading another document. Retry shortly.");
    try { return work.get(); } finally { extraction.release(); }
  }
}
