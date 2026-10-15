package com.sih26190.dms.foli;

import com.sih26190.dms.model.User;
import java.util.*;
import java.util.function.Consumer;
import org.springframework.stereotype.Service;
import static com.sih26190.dms.foli.FoliData.*;

/** Bounded, expiring RAM only. Every hit rereads and reauthorizes the original. */
@Service
public class FoliIndex {
  private record Entry(Snapshot snapshot, long expires) {}
  private final Map<String, Entry> cache = new LinkedHashMap<>(16, .75f, true);
  private final AuthorizedDocumentResolver resolver;
  private final FoliExtractionService extraction;
  private final FoliProperties config;
  private final FoliWorkGate gate;
  public FoliIndex(AuthorizedDocumentResolver resolver, FoliExtractionService extraction, FoliProperties config, FoliWorkGate gate) {
    this.resolver = resolver; this.extraction = extraction; this.config = config; this.gate = gate;
  }
  public Snapshot read(String id, User user, Consumer<String> progress) {
    Source source = resolver.open(id, user);
    String prefix = user.getId() + ":" + id + ":";
    String key = prefix + source.document().version() + ":" + source.hash() + ":" + FoliExtractionService.VERSION;
    synchronized (cache) {
      cache.entrySet().removeIf(e -> e.getValue().expires < System.currentTimeMillis()
          || (e.getKey().startsWith(prefix) && !e.getKey().equals(key)));
      Entry hit = cache.get(key); if (hit != null) return hit.snapshot;
    }
    Snapshot snapshot = gate.reading(() -> extraction.extract(source, progress));
    Source current = resolver.open(id, user);
    if (!current.hash().equals(snapshot.hash()) || !current.document().version().equals(snapshot.document().version()))
      throw AuthorizedDocumentResolver.failure("SOURCE_CHANGED", "Source changed while reading. Select it again.");
    synchronized (cache) {
      cache.put(key, new Entry(snapshot, System.currentTimeMillis() + config.getRetentionSeconds()*1000L));
      while (cache.size() > 8 || cache.values().stream().mapToInt(e -> e.snapshot.manifest().characters()).sum() > config.getCacheCharacters())
        cache.remove(cache.keySet().iterator().next());
    }
    return snapshot;
  }
  public void forget(User user) { synchronized (cache) { cache.keySet().removeIf(k -> k.startsWith(user.getId() + ":")); } }
  @org.springframework.scheduling.annotation.Scheduled(fixedDelay = 30000)
  public void expire() { synchronized (cache) { cache.entrySet().removeIf(e -> e.getValue().expires < System.currentTimeMillis()); } }
}
