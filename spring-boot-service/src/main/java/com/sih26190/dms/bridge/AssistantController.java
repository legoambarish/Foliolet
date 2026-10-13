package com.sih26190.dms.bridge;

import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;
import java.security.Principal;
import java.util.*;
import java.util.concurrent.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/bridge/assistant")
@ConditionalOnProperty(name = "bridge.enabled", havingValue = "true")
public class AssistantController {
  private final AssistantService service;
  private final UserRepository users;
  private final ExecutorService executor =
      new ThreadPoolExecutor(
          1,
          1,
          30,
          TimeUnit.SECONDS,
          new ArrayBlockingQueue<>(8),
          new ThreadPoolExecutor.AbortPolicy());

  public AssistantController(AssistantService service, UserRepository users) {
    this.service = service;
    this.users = users;
  }

  private User user(Principal p) {
    return users.findByUsername(p.getName()).orElseThrow();
  }

  @GetMapping("/documents")
  public Object documents(Principal p) {
    return service.documents(user(p));
  }

  @GetMapping("/history")
  public Object history(Principal p) {
    return service.history(user(p));
  }

  @PostMapping("/history/{id}/delete")
  public Object delete(Principal p, @PathVariable String id) {
    service.delete(user(p), id);
    return Map.of("status", "DELETED");
  }

  @PostMapping("/search")
  public Object search(Principal p, @RequestBody Map<String, Object> input) throws Exception {
    return service.search(user(p), input);
  }

  @PostMapping("/chat")
  public Object chat(Principal p, @RequestBody Map<String, Object> input) throws Exception {
    return service.chat(user(p), input);
  }

  @PostMapping(value = "/stream", produces = "text/event-stream")
  public SseEmitter stream(Principal p, @RequestBody Map<String, Object> input) {
    var user = user(p);
    var emitter = new SseEmitter(90000L);
    var completed = new java.util.concurrent.atomic.AtomicBoolean(false);
    var task =
        executor.submit(
            () -> {
              try {
                emitter.send(SseEmitter.event().name("state").data(Map.of("state", "retrieving")));
                var result = service.chat(user, input);
                emitter.send(SseEmitter.event().name("result").data(result));
                completed.set(true);
                emitter.complete();
              } catch (Exception e) {
                try {
                  emitter.send(
                      SseEmitter.event()
                          .name("error")
                          .data(
                              Map.of(
                                  "message",
                                  "Document assistance unavailable; no action was performed")));
                  emitter.complete();
                } catch (Exception ignored) {
                  emitter.completeWithError(e);
                }
              }
            });
    Runnable cancel =
        () -> {
          if (!completed.get()) task.cancel(true);
        };
    emitter.onTimeout(cancel);
    emitter.onCompletion(cancel);
    emitter.onError(error -> cancel.run());
    return emitter;
  }

  @ExceptionHandler(SecurityException.class)
  public org.springframework.http.ResponseEntity<?> denied(SecurityException e) {
    return org.springframework.http.ResponseEntity.status(403)
        .body(Map.of("message", e.getMessage()));
  }

  @ExceptionHandler(org.springframework.web.server.ResponseStatusException.class)
  public org.springframework.http.ResponseEntity<?> statusError(
      org.springframework.web.server.ResponseStatusException e) {
    return org.springframework.http.ResponseEntity.status(e.getStatusCode())
        .body(Map.of("message", "Document not available to this owner"));
  }

  @ExceptionHandler(IllegalArgumentException.class)
  public org.springframework.http.ResponseEntity<?> invalid(IllegalArgumentException e) {
    return org.springframework.http.ResponseEntity.badRequest()
        .body(Map.of("message", e.getMessage()));
  }

  @ExceptionHandler(Exception.class)
  public org.springframework.http.ResponseEntity<?> unavailable(Exception e) {
    return org.springframework.http.ResponseEntity.status(503)
        .body(Map.of("message", "Document assistance unavailable"));
  }

  @jakarta.annotation.PreDestroy
  public void close() {
    executor.shutdownNow();
  }
}
