package com.sih26190.dms.bridge;

import com.sih26190.dms.model.*;
import com.sih26190.dms.selective.*;
import java.util.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/** Plans are untrusted proposals. Only a holder-key approval enables deterministic execution. */
@Service
@ConditionalOnProperty(name = "bridge.enabled", havingValue = "true")
public class PlanService {
  public static final List<String> STEPS =
      List.of(
          "select_document",
          "select_facts",
          "propose_facts_for_confirmation",
          "anchor_if_needed",
          "create_grant",
          "make_qr");
  private final BridgeService bridge;
  private final BridgeItems items;
  private final PrivateVault vault;
  private final TransactionTemplate tx;
  private final BridgeChain chain;
  private final AssistantService assistant;

  public PlanService(
      BridgeService bridge,
      BridgeItems items,
      PrivateVault vault,
      PlatformTransactionManager manager,
      BridgeChain chain,
      AssistantService assistant) {
    this.bridge = bridge;
    this.items = items;
    this.vault = vault;
    this.tx = new TransactionTemplate(manager);
    this.chain = chain;
    this.assistant = assistant;
  }

  private Map<String, Object> read(BridgeItem item) {
    return BridgeProtocol.parse(vault.open(item.getEncryptedPayload(), item.getId()));
  }

  private void write(BridgeItem item, Map<String, Object> payload) {
    item.setEncryptedPayload(vault.seal(BridgeProtocol.stable(payload), item.getId()));
    items.saveAndFlush(item);
  }

  private BridgeItem own(String id, User user) {
    var item = items.lock(id).orElseThrow(() -> new IllegalArgumentException("Unknown plan"));
    if (!item.getKind().equals("PLAN") || !item.getOwner().equals(user.getUsername()))
      throw new SecurityException("Plan owner required");
    return item;
  }

  public static void validateCandidate(
      Map<String, Object> candidate, Map<String, Object> expected) {
    BridgeProtocol.exact(
        candidate,
        "credentialId",
        "requestId",
        "claims",
        "purpose",
        "verifier",
        "expiresAt",
        "maxOpens",
        "steps");
    if (!BridgeProtocol.stable(candidate).equals(BridgeProtocol.stable(expected)))
      throw new IllegalArgumentException(
          "Plan contains an unsupported step, recipient, fact, policy or lifetime");
  }

  public static byte[] approval(long chainId, String registry, Map<String, Object> plan) {
    return BridgeProtocol.typed(
        chainId,
        registry,
        BridgeProtocol.concat(
            BridgeProtocol.type(
                "PlanApproval(bytes32 planHash,bytes32 requestHash,bytes32 nonce,uint64"
                    + " expiresAt)"),
            BridgeProtocol.word(BridgeProtocol.hash(plan)),
            BridgeProtocol.word(plan.get("requestHash").toString()),
            BridgeProtocol.word(plan.get("nonce").toString()),
            BridgeProtocol.number(((Number) plan.get("expiresAt")).longValue())));
  }

  public Map<String, Object> propose(User user, Map<String, Object> input) {
    BridgeService.role(user, Role.HOLDER);
    if (!Set.of("credentialId", "requestId", "idempotencyKey", "candidate", "intent")
        .containsAll(input.keySet()))
      throw new IllegalArgumentException("Unsupported plan input fields");
    String credentialId = BridgeService.text(input, "credentialId"),
        requestId = BridgeService.text(input, "requestId"),
        key = BridgeService.text(input, "idempotencyKey");
    if (!key.matches("[a-zA-Z0-9_-]{12,100}"))
      throw new IllegalArgumentException("Bounded idempotency key required");
    String id = org.web3j.crypto.Hash.sha3String("plan:" + user.getUsername() + ":" + key);
    return tx.execute(
        status -> {
          var existing = items.findById(id);
          if (existing.isPresent()) {
            var saved = read(existing.get());
            if (!saved.get("inputHash").equals(BridgeProtocol.hash(input)))
              throw new IllegalArgumentException("Idempotency key reused for another plan");
            return view(existing.get());
          }
          var bundle = bridge.draft(user, requestId, credentialId);
          var request = BridgeService.map(bundle.get("request"));
          var candidate =
              Map.<String, Object>of(
                  "credentialId",
                  credentialId,
                  "requestId",
                  requestId,
                  "claims",
                  request.get("claims"),
                  "purpose",
                  request.get("purpose"),
                  "verifier",
                  request.get("verifier"),
                  "expiresAt",
                  request.get("expiresAt"),
                  "maxOpens",
                  1,
                  "steps",
                  STEPS);
          if (input.containsKey("candidate"))
            validateCandidate(BridgeService.map(input.get("candidate")), candidate);
          var proposal =
              input.containsKey("intent")
                  ? assistant.planProposal(BridgeService.text(input, "intent"), candidate)
                  : Map.of(
                      "candidate",
                      candidate,
                      "modelUsed",
                      false,
                      "status",
                      "MANUAL_PLAN",
                      "explanation",
                      "Exact typed API plan");
          var plan = new LinkedHashMap<String, Object>(candidate);
          plan.put("id", id);
          plan.put("requestHash", BridgeProtocol.hash(request));
          plan.put("nonce", request.get("nonce"));
          plan.put("bundleHash", BridgeProtocol.hash(bundle));
          plan.put("proposalStatus", proposal.get("status"));
          plan.put("modelUsed", proposal.get("modelUsed"));
          plan.put("explanation", proposal.get("explanation"));
          var item = new BridgeItem();
          item.setId(id);
          item.setKind("PLAN");
          item.setOwner(user.getUsername());
          item.setStatus("PROPOSED");
          item.setCreatedAt(BridgeService.now());
          item.setExpiresAt(BridgeService.number(request, "expiresAt"));
          write(
              item,
              new LinkedHashMap<>(
                  Map.of(
                      "plan",
                      plan,
                      "bundle",
                      bundle,
                      "inputHash",
                      BridgeProtocol.hash(input),
                      "events",
                      new ArrayList<>(
                          List.of(
                              Map.of(
                                  "state",
                                  "PROPOSED",
                                  "at",
                                  BridgeService.now(),
                                  "detail",
                                  "No grant, anchoring or disclosure performed"))))));
          return view(item);
        });
  }

  private Map<String, Object> view(BridgeItem item) {
    var p = read(item);
    return Map.of(
        "id",
        item.getId(),
        "status",
        item.getStatus(),
        "plan",
        p.get("plan"),
        "planHash",
        BridgeProtocol.hash(p.get("plan")),
        "bundle",
        p.get("bundle"),
        "events",
        p.get("events"),
        "result",
        p.getOrDefault("result", Map.of()));
  }

  public Map<String, Object> approve(User user, String id, Map<String, Object> input) {
    BridgeService.role(user, Role.HOLDER);
    return tx.execute(
        status -> {
          var item = own(id, user);
          if (!item.getStatus().equals("PROPOSED") || item.getExpiresAt() <= BridgeService.now())
            throw new IllegalArgumentException("Plan is not awaiting approval");
          var p = read(item);
          var plan = BridgeService.map(p.get("plan"));
          var bundle = BridgeService.map(p.get("bundle"));
          if (!BridgeProtocol.hash(plan).equals(BridgeService.text(input, "planHash")))
            throw new IllegalArgumentException("Approval card changed");
          var fresh =
              bridge.draft(
                  user, plan.get("requestId").toString(), plan.get("credentialId").toString());
          if (!BridgeProtocol.hash(fresh).equals(plan.get("bundleHash")))
            throw new IllegalArgumentException("Evidence or request changed; prepare a new plan");
          String holder = BridgeService.text(BridgeService.map(bundle.get("credential")), "holder");
          if (!BridgeProtocol.eq(
              BridgeProtocol.recover(
                  approval(chain.chainId, chain.registry, plan),
                  BridgeService.text(input, "planSignature")),
              holder)) throw new IllegalArgumentException("Holder plan approval signature differs");
          p.put("holderSignature", BridgeService.text(input, "holderSignature"));
          p.put("planSignature", BridgeService.text(input, "planSignature"));
          event(p, "APPROVED", "Holder signed exact plan and presentation");
          item.setStatus("APPROVED");
          write(item, p);
          return view(item);
        });
  }

  public Map<String, Object> cancel(User user, String id) {
    return tx.execute(
        status -> {
          var item = own(id, user);
          if (!Set.of("PROPOSED", "APPROVED").contains(item.getStatus()))
            throw new IllegalArgumentException("Plan cannot be cancelled in this state");
          var p = read(item);
          event(p, "CANCELLED", "No disclosure executed");
          item.setStatus("CANCELLED");
          write(item, p);
          return view(item);
        });
  }

  public Map<String, Object> execute(User user, String id) {
    BridgeService.role(user, Role.HOLDER);
    try {
      return tx.execute(
          status -> {
            var item = own(id, user);
            if (item.getStatus().equals("COMPLETED")) return view(item);
            if (!item.getStatus().equals("APPROVED") || item.getExpiresAt() <= BridgeService.now())
              throw new IllegalArgumentException("Explicit unexpired holder approval required");
            var p = read(item);
            var plan = BridgeService.map(p.get("plan"));
            for (String step : STEPS) {
              event(
                  p,
                  step,
                  switch (step) {
                    case "anchor_if_needed" ->
                        "Existing issuer anchor required; this plan cannot issue or upgrade"
                            + " authority";
                    case "propose_facts_for_confirmation" ->
                        "Exact existing issuer-confirmed facts only; no model facts auto-confirmed";
                    default -> "Deterministic allowlisted step";
                  });
            }
            try {
              var grant =
                  bridge.grant(
                      user,
                      Map.of(
                          "requestId",
                          plan.get("requestId"),
                          "credentialId",
                          plan.get("credentialId"),
                          "holderSignature",
                          p.get("holderSignature")));
              p.put("result", grant);
              event(p, "COMPLETED", "One-opening grant and QR discovery URL ready");
              item.setStatus("COMPLETED");
              write(item, p);
              return view(item);
            } catch (Exception e) {
              throw new IllegalArgumentException(e.getMessage(), e);
            }
          });
    } catch (RuntimeException failure) {
      tx.executeWithoutResult(
          status -> {
            var item = own(id, user);
            if (item.getStatus().equals("APPROVED")) {
              var p = read(item);
              event(p, "FAILED", "Execution refused; no grant committed");
              item.setStatus("FAILED");
              write(item, p);
            }
          });
      throw failure;
    }
  }

  private static void event(Map<String, Object> p, String state, String detail) {
    ((List<Object>) p.get("events"))
        .add(Map.of("state", state, "at", BridgeService.now(), "detail", detail));
  }

  public Map<String, Object> status(User user, String id) {
    return tx.execute(status -> view(own(id, user)));
  }
}
