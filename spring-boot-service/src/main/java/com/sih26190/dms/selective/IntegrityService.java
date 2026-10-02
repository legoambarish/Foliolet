package com.sih26190.dms.selective;

import com.sih26190.dms.model.User;
import com.sih26190.dms.selective.WalletDtos.*;
import com.sih26190.dms.selective.model.*;
import com.sih26190.dms.selective.repository.*;
import com.sih26190.dms.service.AuditService;
import java.time.Instant;
import java.util.*;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import org.web3j.crypto.Hash;
import org.web3j.utils.Numeric;

@Service
public class IntegrityService {
  private static final String ZERO = "0x" + "00".repeat(32);
  private final IntegrityAgentRepository agents;
  private final FirstSeenObservationRepository observations;
  private final PrivateVault vault;
  private final MerkleTreeService merkle;
  private final ClaimCanonicalizer canonical;
  private final AuditService audit;

  public IntegrityService(
      IntegrityAgentRepository agents,
      FirstSeenObservationRepository observations,
      PrivateVault vault,
      MerkleTreeService merkle,
      ClaimCanonicalizer canonical,
      AuditService audit) {
    this.agents = agents;
    this.observations = observations;
    this.vault = vault;
    this.merkle = merkle;
    this.canonical = canonical;
    this.audit = audit;
  }

  @Transactional
  public Map<String, Object> create(User owner, String label) {
    var agent = new IntegrityAgent();
    agent.id = UUID.randomUUID().toString();
    agent.ownerId = owner.getId();
    agent.label = canonical.text(label, 100);
    String secret = merkle.randomHex();
    agent.encryptedSecret = vault.seal(secret, agent.id);
    agent.createdAt = Instant.now();
    agent.lastDigest = ZERO;
    agents.save(agent);
    audit.logWallet(owner, null, null, "INTEGRITY_AGENT_PAIRED");
    return Map.of("agentId", agent.id, "secret", secret, "label", agent.label);
  }

  public List<Map<String, Object>> list(User owner) {
    return agents.findByOwnerIdOrderByCreatedAtDesc(owner.getId()).stream()
        .map(
            a ->
                Map.<String, Object>of(
                    "id", a.id, "label", a.label, "active", a.active, "createdAt", a.createdAt))
        .toList();
  }

  @Transactional
  public void revoke(User owner, String id) {
    var a = agents.locked(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
    if (!a.ownerId.equals(owner.getId())) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
    a.active = false;
    agents.save(a);
    audit.logWallet(owner, null, null, "INTEGRITY_AGENT_REVOKED");
  }

  public static byte[] message(ObservationInput r) {
    return MerkleTreeService.encode(
        "first-seen-v1",
        r.agentId(),
        r.itemId(),
        r.filename(),
        r.sha256(),
        Long.toString(r.observedAt().getEpochSecond()),
        Long.toString(r.sequence()),
        r.previousDigest());
  }

  public static String hmac(byte[] key, byte[] bytes) {
    try {
      Mac mac = Mac.getInstance("HmacSHA256");
      mac.init(new SecretKeySpec(key, "HmacSHA256"));
      return HexFormat.of().formatHex(mac.doFinal(bytes));
    } catch (Exception e) {
      throw new IllegalStateException(e);
    }
  }

  @Transactional
  public Map<String, Object> observe(ObservationInput input) {
    var agent =
        agents
            .locked(input.agentId())
            .orElseThrow(
                () -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Unknown agent"));
    if (!agent.active) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Agent revoked");
    UUID.fromString(input.itemId());
    canonical.text(input.filename(), 255);
    byte[] msg = message(input);
    String expected =
        hmac(MerkleTreeService.hex32(vault.open(agent.encryptedSecret, agent.id)), msg);
    if (!java.security.MessageDigest.isEqual(
        expected.getBytes(java.nio.charset.StandardCharsets.US_ASCII),
        input.signature().getBytes(java.nio.charset.StandardCharsets.US_ASCII)))
      throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid agent signature");
    String digest = Numeric.toHexString(Hash.sha3(msg));
    if (input.sequence() <= agent.sequence) {
      var previous =
          observations
              .findByAgentIdAndSequence(agent.id, input.sequence())
              .orElseThrow(
                  () -> new ResponseStatusException(HttpStatus.CONFLICT, "Sequence replay"));
      if (!previous.digest.equals(digest))
        throw new ResponseStatusException(HttpStatus.CONFLICT, "Sequence replay");
      return Map.of("observationId", previous.id, "digest", digest, "sequence", input.sequence());
    }
    if (input.sequence() != agent.sequence + 1 || !input.previousDigest().equals(agent.lastDigest))
      throw new ResponseStatusException(
          HttpStatus.CONFLICT, "Agent sequence or previous digest mismatch");
    Instant now = Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS);
    if (input.observedAt().isAfter(now.plusSeconds(60))
        || input.observedAt().isBefore(now.minusSeconds(86400)))
      throw new ResponseStatusException(
          HttpStatus.BAD_REQUEST, "Observation must arrive within 24 hours; use a current report");
    var row = new FirstSeenObservation();
    row.id = UUID.randomUUID().toString();
    row.agentId = agent.id;
    row.ownerId = agent.ownerId;
    row.itemId = input.itemId();
    row.filename = input.filename();
    row.sha256 = input.sha256();
    row.digest = digest;
    row.sequence = input.sequence();
    row.receivedAt = now;
    row.observedAt = input.observedAt();
    observations.save(row);
    agent.sequence = input.sequence();
    agent.lastDigest = digest;
    agents.save(agent);
    return Map.of("observationId", row.id, "digest", digest, "sequence", input.sequence());
  }

  public List<Map<String, Object>> observations(User user) {
    return observations.findByOwnerIdOrderByReceivedAtDesc(user.getId()).stream()
        .map(
            o ->
                Map.<String, Object>of(
                    "id",
                    o.id,
                    "filename",
                    o.filename,
                    "agentId",
                    o.agentId,
                    "itemId",
                    o.itemId,
                    "sha256",
                    o.sha256,
                    "receivedAt",
                    o.receivedAt))
        .toList();
  }

  public Provenance provenance(User owner, String observationId, byte[] document) {
    if (observationId == null || observationId.isBlank())
      return new Provenance(
          "SELF_ENROLLED",
          "Holder-confirmed facts. Inclusion proves commitment membership, not issuer authenticity"
              + " or extraction from document bytes.",
          null,
          null,
          0,
          false,
          false,
          null);
    var chosen =
        observations
            .findById(observationId)
            .orElseThrow(() -> new IllegalArgumentException("Observation not found"));
    if (!chosen.ownerId.equals(owner.getId()))
      throw new ResponseStatusException(HttpStatus.NOT_FOUND);
    var agent = agents.findById(chosen.agentId).orElseThrow();
    if (!agent.active)
      throw new IllegalArgumentException("Selected integrity agent has been revoked");
    var history =
        observations.findByAgentIdAndItemIdOrderBySequenceAsc(chosen.agentId, chosen.itemId);
    String first = history.get(0).sha256;
    boolean match = first.equals(PrivateVault.sha256(document));
    boolean changed = history.stream().anyMatch(o -> !o.sha256.equals(first));
    String level = match && !changed ? "FIRST_SEEN_TRACKED" : "SELF_ENROLLED";
    String detail =
        match && !changed
            ? "At enrollment, uploaded bytes matched every observation then received from an"
                  + " authenticated holder-paired agent. This is a sampled continuity snapshot, not"
                  + " an independent issuer attestation. Facts remain holder-confirmed."
            : "First-seen continuity was not established: bytes differed or a change was observed."
                  + " Facts remain self-enrolled.";
    return new Provenance(
        level,
        detail,
        history.get(0).receivedAt,
        history.get(history.size() - 1).receivedAt,
        history.size(),
        changed,
        match,
        agent.id);
  }
}
