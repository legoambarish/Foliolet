package com.sih26190.dms.bridge;

import com.sih26190.dms.model.*;
import com.sih26190.dms.repository.UserRepository;
import com.sih26190.dms.selective.*;
import java.math.*;
import java.time.*;
import java.util.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.web3j.abi.datatypes.*;
import org.web3j.abi.datatypes.generated.*;
import org.web3j.crypto.*;
import org.web3j.utils.Numeric;

@Service
@ConditionalOnProperty(name = "bridge.enabled", havingValue = "true")
public class BridgeService {
  private final BridgeItems items;
  private final PrivateVault vault;
  private final MerkleTreeService merkle;
  private final ClaimCanonicalizer canonical;
  private final BridgeChain chain;
  private final WalletService wallet;
  private final UserRepository users;
  private final boolean demo;
  private final org.springframework.transaction.support.TransactionTemplate transactions;
  public static final Map<String, Map<String, List<String>>> TYPES =
      Map.of(
          "internship-eligibility/v1",
              Map.of(
                  "education.cgpa_at_least_8_5",
                  List.of("boolean", "CGPA at least 8.5", "education.cgpa"),
                  "education.enrolled",
                  List.of("boolean", "Currently enrolled", ""),
                  "subject.name",
                  List.of("string", "Name", "")),
          "income-evidence/v1",
              Map.of(
                  "employment.monthly_income",
                  List.of("decimal", "Monthly income", ""),
                  "employment.currency",
                  List.of("string", "Currency", ""),
                  "employment.active",
                  List.of("boolean", "Employment active", ""),
                  "subject.name",
                  List.of("string", "Name", "")));

  public BridgeService(
      BridgeItems items,
      PrivateVault vault,
      MerkleTreeService merkle,
      ClaimCanonicalizer canonical,
      BridgeChain chain,
      WalletService wallet,
      UserRepository users,
      org.springframework.transaction.PlatformTransactionManager manager,
      org.springframework.core.env.Environment environment) {
    this.items = items;
    this.vault = vault;
    this.merkle = merkle;
    this.canonical = canonical;
    this.chain = chain;
    this.wallet = wallet;
    this.users = users;
    this.demo = environment.getProperty("bridge.demo", Boolean.class, false);
    this.transactions = new org.springframework.transaction.support.TransactionTemplate(manager);
  }

  public static long now() {
    return Instant.now().getEpochSecond();
  }

  public static Map<String, Object> map(Object value) {
    if (!(value instanceof Map<?, ?>)) throw new IllegalArgumentException("Object required");
    return (Map<String, Object>) value;
  }

  public static String text(Map<String, Object> value, String key) {
    if (!(value.get(key) instanceof String s))
      throw new IllegalArgumentException("Text required: " + key);
    return s;
  }

  public static long number(Map<String, Object> value, String key) {
    if (!(value.get(key) instanceof Number n) || n instanceof Double || n instanceof Float)
      throw new IllegalArgumentException("Integer required: " + key);
    return n.longValue();
  }

  public static void role(User user, Role role) {
    if (user.getRole() != role) throw new SecurityException("This action requires " + role);
  }

  private Map<String, Object> payload(BridgeItem item) {
    return BridgeProtocol.parse(vault.open(item.getEncryptedPayload(), item.getId()));
  }

  private BridgeItem store(
      String kind,
      String id,
      String owner,
      String recipient,
      String status,
      long expiry,
      Map<String, Object> payload) {
    var item = new BridgeItem();
    item.setKind(kind);
    item.setId(id);
    item.setOwner(owner);
    item.setRecipient(recipient);
    item.setStatus(status);
    item.setCreatedAt(now());
    item.setExpiresAt(expiry);
    item.setEncryptedPayload(vault.seal(BridgeProtocol.stable(payload), id));
    return items.saveAndFlush(item);
  }

  private BridgeItem owned(String id, User user, String kind) {
    var item = items.findById(id).orElseThrow(() -> new IllegalArgumentException("Unknown item"));
    if (!kind.equals(item.getKind()) || !user.getUsername().equals(item.getOwner()))
      throw new SecurityException("Owner access required");
    return item;
  }

  public Map<String, Object> liveGrants(User user) {
    role(user, Role.GOVERNANCE);
    if (!demo) throw new SecurityException("Demo operation disabled");
    return Map.of(
        "count",
        items.findAll().stream()
            .filter(
                i ->
                    i.getKind().equals("GRANT")
                        && i.getStatus().equals("ACTIVE")
                        && i.getExpiresAt() > now()
                        && i.getOpens() < 1)
            .count());
  }

  public Map<String, Object> state(User user) {
    var result = new LinkedHashMap<String, Object>();
    result.put("username", user.getUsername());
    result.put("role", user.getRole().name());
    result.put("demo", demo);
    result.put("claimTypes", TYPES);
    result.put("registry", chain.registry);
    result.put("governance", chain.governance);
    result.put("chainId", chain.chainId);
    result.put(
        "credentials",
        (user.getRole() == Role.HOLDER
                ? items.findByKindAndRecipientOrderByCreatedAtDesc("CREDENTIAL", user.getUsername())
                : items.findByKindAndOwnerOrderByCreatedAtDesc("CREDENTIAL", user.getUsername()))
            .stream().map(this::credentialView).toList());
    result.put(
        "requests",
        (user.getRole() == Role.HOLDER
                ? items.findByKindAndRecipientOrderByCreatedAtDesc("REQUEST", user.getUsername())
                : items.findByKindAndOwnerOrderByCreatedAtDesc("REQUEST", user.getUsername()))
            .stream()
                .map(i -> Map.of("id", i.getId(), "status", i.getStatus(), "request", payload(i)))
                .toList());
    result.put(
        "grants",
        items.findByKindAndOwnerOrderByCreatedAtDesc("GRANT", user.getUsername()).stream()
            .map(
                i ->
                    Map.of(
                        "id",
                        i.getId(),
                        "status",
                        i.getStatus(),
                        "expiresAt",
                        i.getExpiresAt(),
                        "opens",
                        i.getOpens()))
            .toList());
    result.put(
        "decisions",
        items.findByKindAndOwnerOrderByCreatedAtDesc("DECISION", user.getUsername()).stream()
            .map(this::payload)
            .toList());
    items
        .findById("key:" + user.getUsername())
        .ifPresent(i -> result.put("holderAddress", payload(i).get("address")));
    if (user.getRole() != Role.HOLDER)
      result.put("signerAddress", chain.signer(user.getUsername()).getAddress());
    try {
      var current = chain.block();
      long block = current.getNumber().longValueExact();
      result.put("readBlock", block);
      result.put("blockTimestamp", current.getTimestamp().longValueExact());
      var authorities = new ArrayList<Map<String, Object>>();
      for (String actor : List.of("university", "employer", "rogue"))
        for (String claimType : TYPES.keySet()) {
          var authority =
              new LinkedHashMap<String, Object>(
                  chain.issuer(chain.signer(actor).getAddress(), claimType, block));
          authority.put("actor", actor);
          authority.put("address", chain.signer(actor).getAddress());
          authority.put("claimType", claimType);
          authorities.add(authority);
        }
      result.put("authorities", authorities);
    } catch (Exception unavailable) {
      result.put("chainStatus", "UNKNOWN");
    }
    return result;
  }

  private Map<String, Object> credentialView(BridgeItem item) {
    var p = payload(item);
    return Map.of(
        "id",
        item.getId(),
        "status",
        item.getStatus(),
        "credential",
        p.get("credential"),
        "values",
        p.get("values"),
        "holder",
        item.getRecipient());
  }

  @Transactional
  public Map<String, Object> bind(User user, Map<String, Object> input) {
    role(user, Role.HOLDER);
    String address = text(input, "address"), sig = text(input, "signature");
    String message = "Foliolet holder binding: " + user.getUsername();
    if (!address.matches("0x[0-9a-fA-F]{40}")
        || !BridgeProtocol.eq(
            address,
            BridgeProtocol.recover(
                Sign.getEthereumMessageHash(
                    message.getBytes(java.nio.charset.StandardCharsets.UTF_8)),
                sig))) throw new IllegalArgumentException("Holder binding signature differs");
    String id = "key:" + user.getUsername();
    if (items.existsById(id)
        && !BridgeProtocol.eq(payload(items.findById(id).orElseThrow()).get("address"), address))
      throw new IllegalArgumentException(
          "Holder key is already bound; demo reset required for rotation");
    if (!items.existsById(id))
      store("KEY", id, user.getUsername(), null, "BOUND", 0, Map.of("address", address));
    return Map.of("address", address, "status", "BOUND");
  }

  public synchronized Map<String, Object> issue(User issuer, Map<String, Object> input)
      throws Exception {
    role(issuer, Role.ISSUER);
    String jobId =
        "issue:" + Hash.sha3String(issuer.getUsername() + ":" + BridgeProtocol.hash(input));
    var existing = items.findById(jobId);
    if (existing.isPresent())
      return finishIssue(
          issuer, owned(text(payload(existing.get()), "credentialId"), issuer, "CREDENTIAL"));
    String id = merkle.randomHex();
    String type = text(input, "claimType"),
        holder = text(input, "holder"),
        source = text(input, "sourceDocumentId");
    if (!TYPES.containsKey(type)) throw new IllegalArgumentException("Unsupported claim type");
    var account =
        users
            .findByUsername(holder)
            .orElseThrow(() -> new IllegalArgumentException("Unknown holder"));
    role(account, Role.HOLDER);
    String holderAddress =
        text(
            payload(
                items
                    .findById("key:" + holder)
                    .orElseThrow(
                        () ->
                            new IllegalArgumentException("Holder must bind a browser key first"))),
            "address");
    var document = wallet.owned(source, issuer);
    if (!PrivateVault.commitment(
            document.documentSalt,
            Numeric.toHexString(Hash.sha3(vault.read(document.filePath, source))))
        .equals(document.documentCommitment))
      throw new IllegalArgumentException("Source document integrity not established");
    var values = new TreeMap<String, String>();
    Map<String, Object> supplied = map(input.get("values"));
    for (var field : TYPES.get(type).entrySet()) {
      String value;
      if (field.getKey().equals("education.cgpa_at_least_8_5")) {
        String cgpa = text(supplied, "education.cgpa");
        var decimal = new BigDecimal(canonical.value("decimal", cgpa));
        if (decimal.signum() < 0 || decimal.compareTo(BigDecimal.TEN) > 0)
          throw new IllegalArgumentException("CGPA must be within 0-10");
        value = Boolean.toString(decimal.compareTo(new BigDecimal("8.5")) >= 0);
      } else value = canonical.value(field.getValue().get(0), text(supplied, field.getKey()));
      if (value.length() > 240
          || (field.getValue().get(0).equals("decimal") && new BigDecimal(value).signum() < 0))
        throw new IllegalArgumentException("Unsupported claim value");
      values.put(field.getKey(), value);
    }
    var expected = new HashSet<>(TYPES.get(type).keySet());
    if (type.startsWith("internship")) {
      expected.remove("education.cgpa_at_least_8_5");
      expected.add("education.cgpa");
    }
    if (!supplied.keySet().equals(expected))
      throw new IllegalArgumentException("Exact typed input fields required");
    var leaves = new ArrayList<MerkleTreeService.Leaf>();
    for (var value : values.entrySet()) {
      var spec = TYPES.get(type).get(value.getKey());
      leaves.add(
          new MerkleTreeService.Leaf(
              value.getKey(),
              spec.get(1),
              spec.get(0),
              value.getValue(),
              spec.get(2),
              merkle.randomHex(),
              leaves.size()));
    }
    String previous = input.getOrDefault("previous", BridgeChain.ZERO).toString();
    int version = 1;
    if (!previous.equals(BridgeChain.ZERO)) {
      var old = owned(previous, issuer, "CREDENTIAL");
      if (!holder.equals(old.getRecipient()))
        throw new IllegalArgumentException("Replacement holder differs");
      version = ((Number) map(payload(old).get("credential")).get("version")).intValue() + 1;
    }
    long expiry = number(input, "expiresAt");
    if (expiry <= now() || expiry > now() + 366 * 86400L)
      throw new IllegalArgumentException("Evidence expiry must be within one year");
    String root = merkle.root(leaves), signer = chain.signer(issuer.getUsername()).getAddress();
    var credential = new LinkedHashMap<String, Object>();
    credential.put("id", id);
    credential.put("root", root);
    credential.put("documentCommitment", document.documentCommitment);
    credential.put("claimType", type);
    credential.put("issuer", signer);
    credential.put("holder", holderAddress);
    credential.put("leafCount", leaves.size());
    credential.put("version", version);
    credential.put("evidenceClass", 2);
    credential.put("expiresAt", expiry);
    // Commit recoverable encrypted evidence before the independent EVM transaction.
    var item =
        transactions.execute(
            status ->
                store(
                    "CREDENTIAL",
                    id,
                    issuer.getUsername(),
                    holder,
                    "ANCHOR_PENDING",
                    expiry,
                    Map.of(
                        "credential",
                        credential,
                        "values",
                        values,
                        "leaves",
                        leaves,
                        "sourceDocumentId",
                        source,
                        "previous",
                        previous)));
    transactions.executeWithoutResult(
        status ->
            store(
                "ISSUE_JOB",
                jobId,
                issuer.getUsername(),
                null,
                "PREPARED",
                expiry,
                Map.of("credentialId", id)));
    return finishIssue(issuer, item);
  }

  private Map<String, Object> finishIssue(User issuer, BridgeItem item) throws Exception {
    if (!item.getOwner().equals(issuer.getUsername()) || !item.getKind().equals("CREDENTIAL"))
      throw new SecurityException("Issuer owner required");
    if (!item.getStatus().equals("ANCHOR_PENDING")) return credentialView(item);
    var saved = payload(item);
    var c = map(saved.get("credential"));
    String previous = saved.get("previous").toString();
    try {
      var onChain = chain.evidence(item.getId(), chain.block().getNumber().longValueExact());
      if (number(onChain, "status") == 0) {
        chain.send(
            issuer.getUsername(),
            "anchor",
            List.of(
                BridgeChain.b(item.getId()),
                BridgeChain.b(text(c, "root")),
                BridgeChain.b(text(c, "documentCommitment")),
                BridgeChain.b(Hash.sha3String(text(c, "claimType"))),
                new Address(text(c, "holder")),
                new Uint32(number(c, "leafCount")),
                new Uint32(number(c, "version")),
                new Uint64(number(c, "expiresAt")),
                new Uint8(2),
                BridgeChain.b(previous)));
        onChain = chain.evidence(item.getId(), chain.block().getNumber().longValueExact());
      }
      for (String field :
          List.of(
              "root",
              "documentCommitment",
              "holder",
              "issuer",
              "leafCount",
              "version",
              "expiresAt",
              "evidenceClass"))
        if (!BridgeProtocol.eq(c.get(field), onChain.get(field)))
          throw new IllegalArgumentException("Pending evidence differs from chain");
      long lifecycle = number(onChain, "status");
      transactions.executeWithoutResult(
          status -> {
            item.setStatus(lifecycle == 1 ? "ACTIVE" : lifecycle == 2 ? "REVOKED" : "SUPERSEDED");
            items.saveAndFlush(item);
            if (!previous.equals(BridgeChain.ZERO)) {
              var old = items.findById(previous).orElseThrow();
              old.setStatus("SUPERSEDED");
              items.save(old);
            }
          });
      return credentialView(item);
    } catch (Exception e) {
      throw new IllegalArgumentException("Issuer anchoring refused: " + e.getMessage());
    }
  }

  public synchronized Map<String, Object> retryIssue(User issuer, String id) throws Exception {
    role(issuer, Role.ISSUER);
    return finishIssue(issuer, owned(id, issuer, "CREDENTIAL"));
  }

  public Map<String, Object> rogueScenario(User user) throws Exception {
    role(user, Role.GOVERNANCE);
    if (!demo) throw new SecurityException("Demo operation disabled");
    String id = merkle.randomHex();
    String converter = chain.signer("rogue").getAddress();
    var block = chain.block();
    var authority =
        chain.issuer(converter, "internship-eligibility/v1", block.getNumber().longValueExact());
    if (Boolean.TRUE.equals(authority.get("recognized")))
      throw new IllegalArgumentException(
          "Rogue actor has been recognized; reset the negative scenario first");
    try {
      chain.send(
          "rogue",
          "anchor",
          List.of(
              BridgeChain.b(id),
              BridgeChain.b(merkle.randomHex()),
              BridgeChain.b(merkle.randomHex()),
              BridgeChain.b(Hash.sha3String("internship-eligibility/v1")),
              new Address(converter),
              new Uint32(1),
              new Uint32(1),
              new Uint64(now() + 3600),
              new Uint8(2),
              BridgeChain.b(BridgeChain.ZERO)));
      throw new IllegalStateException("Unexpected authority acceptance");
    } catch (IllegalArgumentException refused) {
      return Map.of(
          "result",
          "FAIL",
          "requirement",
          "issuer authority",
          "reason",
          "Real EVM transaction refused the unrecognized converter. A converter signature cannot"
              + " become university authority.",
          "converter",
          converter,
          "attemptedCredentialId",
          id,
          "readBlock",
          chain.block().getNumber().longValueExact(),
          "recognized",
          false);
    }
  }

  @Transactional
  public Map<String, Object> governance(User user, Map<String, Object> input) throws Exception {
    role(user, Role.GOVERNANCE);
    String action = text(input, "action"), address = text(input, "issuer");
    if (!address.matches("0x[0-9a-fA-F]{40}"))
      throw new IllegalArgumentException("Invalid issuer address");
    var args = new ArrayList<Type>();
    args.add(new Address(address));
    String function;
    switch (action) {
      case "recognize" -> {
        String type = text(input, "claimType");
        if (!TYPES.containsKey(type)) throw new IllegalArgumentException("Unsupported type");
        function = "recognize";
        args.add(new Utf8String(canonical.text(text(input, "name"), 120)));
        args.add(BridgeChain.b(Hash.sha3String(type)));
      }
      case "scope" -> {
        String type = text(input, "claimType");
        if (!TYPES.containsKey(type) || !(input.get("allowed") instanceof Boolean))
          throw new IllegalArgumentException("Invalid scope");
        function = "setScope";
        args.add(BridgeChain.b(Hash.sha3String(type)));
        args.add(new Bool((Boolean) input.get("allowed")));
      }
      case "suspend", "reinstate" -> {
        function = "suspend";
        args.add(new Bool(action.equals("suspend")));
      }
      default -> throw new IllegalArgumentException("Unsupported governance action");
    }
    var tx = chain.send(user.getUsername(), function, args);
    return Map.of("transaction", tx.getTransactionHash(), "block", tx.getBlockNumber().longValue());
  }

  @Transactional
  public void revoke(User user, String id) throws Exception {
    role(user, Role.ISSUER);
    var item = owned(id, user, "CREDENTIAL");
    chain.send(user.getUsername(), "revoke", List.of(BridgeChain.b(id)));
    item.setStatus("REVOKED");
    items.save(item);
  }

  @Transactional
  public Map<String, Object> request(User verifier, Map<String, Object> input) {
    role(verifier, Role.VERIFIER);
    String holder = text(input, "holder");
    role(
        users
            .findByUsername(holder)
            .orElseThrow(() -> new IllegalArgumentException("Unknown holder")),
        Role.HOLDER);
    boolean internship = verifier.getUsername().equals("internship-verifier");
    String type = internship ? "internship-eligibility/v1" : "income-evidence/v1",
        issuer = chain.signer(internship ? "university" : "employer").getAddress();
    long expiry = number(input, "expiresAt"), retention = number(input, "retentionDays");
    if (expiry <= now() || expiry > now() + 604800 || retention < 0 || retention > 30)
      throw new IllegalArgumentException("Request deadline or retention outside bounds");
    String purpose = canonical.text(text(input, "purpose"), 240);
    if (purpose.length() < 3) throw new IllegalArgumentException("Purpose is required");
    List<String> claims =
        internship
            ? List.of("education.cgpa_at_least_8_5", "education.enrolled")
            : List.of("employment.active", "employment.currency", "employment.monthly_income");
    var policy =
        Map.of(
            "claimType",
            type,
            "acceptedIssuers",
            List.of(issuer),
            "evidenceClasses",
            List.of(2),
            "maxReadAgeSeconds",
            120,
            "holderBinding",
            true,
            "requiredValues",
            internship
                ? Map.of("education.cgpa_at_least_8_5", "true", "education.enrolled", "true")
                : Map.of("employment.active", "true", "employment.currency", "INR"),
            "minimumValues",
            internship ? Map.of() : Map.of("employment.monthly_income", "25000"));
    String id = merkle.randomHex();
    var request = new LinkedHashMap<String, Object>();
    request.put("id", id);
    request.put("verifier", chain.signer(verifier.getUsername()).getAddress());
    request.put("purpose", purpose);
    request.put("retentionDays", retention);
    request.put("claims", claims);
    request.put("nonce", merkle.randomHex());
    request.put("issuedAt", now());
    request.put("expiresAt", expiry);
    request.put("policy", policy);
    store("REQUEST", id, verifier.getUsername(), holder, "OPEN", expiry, request);
    return Map.of(
        "request",
        request,
        "signature",
        BridgeProtocol.sign(
            BridgeProtocol.request(chain.chainId, chain.registry, request),
            chain.signer(verifier.getUsername())));
  }

  private Map<String, Object> requestForHolder(String id, User holder) {
    var item =
        items.findById(id).orElseThrow(() -> new IllegalArgumentException("Unknown request"));
    if (!item.getKind().equals("REQUEST") || !holder.getUsername().equals(item.getRecipient()))
      throw new SecurityException("Request is assigned to another holder");
    if (!item.getStatus().equals("OPEN") || item.getExpiresAt() <= now())
      throw new IllegalArgumentException("Request expired or consumed");
    return payload(item);
  }

  private List<MerkleTreeService.Leaf> leaves(Map<String, Object> payload) {
    return ((List<?>) payload.get("leaves"))
        .stream()
            .map(v -> BridgeProtocol.JSON.convertValue(v, MerkleTreeService.Leaf.class))
            .toList();
  }

  public Map<String, Object> draft(User holder, String requestId, String credentialId) {
    role(holder, Role.HOLDER);
    var r = requestForHolder(requestId, holder);
    var item =
        items
            .findById(credentialId)
            .orElseThrow(() -> new IllegalArgumentException("Unknown evidence"));
    if (!item.getKind().equals("CREDENTIAL")
        || !holder.getUsername().equals(item.getRecipient())
        || !item.getStatus().equals("ACTIVE"))
      throw new SecurityException("Own active evidence required");
    var p = payload(item);
    var all = leaves(p);
    List<String> requested = (List<String>) r.get("claims");
    var selected =
        all.stream()
            .filter(l -> requested.contains(l.path()))
            .map(l -> new MerkleTreeService.RevealedClaim(l, merkle.proof(all, l.index())))
            .toList();
    if (selected.size() != requested.size())
      throw new IllegalArgumentException("Evidence does not provide requested typed fields");
    String verifier = items.findById(requestId).orElseThrow().getOwner();
    var bundle = new LinkedHashMap<String, Object>();
    bundle.put("format", "foliolet-evidence-bridge-v1");
    bundle.put("registry", chain.registry);
    bundle.put("chainId", chain.chainId);
    bundle.put("credential", p.get("credential"));
    bundle.put("request", r);
    bundle.put(
        "requestSignature",
        BridgeProtocol.sign(
            BridgeProtocol.request(chain.chainId, chain.registry, r), chain.signer(verifier)));
    bundle.put("claims", selected);
    bundle.put("holderSignature", "0x" + "00".repeat(65));
    return BridgeProtocol.parse(BridgeProtocol.stable(bundle));
  }

  private String disclosures(List<?> claims) {
    return Numeric.toHexString(
        Hash.sha3(
            claims.stream()
                .map(
                    c ->
                        merkle.leafHash(
                            BridgeProtocol.JSON.convertValue(
                                map(c).get("leaf"), MerkleTreeService.Leaf.class)))
                .map(Numeric::hexStringToByteArray)
                .reduce(new byte[0], (a, b) -> BridgeProtocol.concat(a, b))));
  }

  @Transactional
  public Map<String, Object> grant(User holder, Map<String, Object> input) throws Exception {
    role(holder, Role.HOLDER);
    String requestId = text(input, "requestId"), credentialId = text(input, "credentialId");
    var bundle = draft(holder, requestId, credentialId);
    bundle.put("holderSignature", text(input, "holderSignature"));
    var evaluation = evaluate(bundle);
    if (!evaluation.get("result").equals("PASS"))
      throw new IllegalArgumentException(
          "Evidence cannot satisfy this request: " + BridgeProtocol.stable(evaluation));
    String token = merkle.randomHex(), id = Hash.sha3String(token);
    long expiry = number(map(bundle.get("request")), "expiresAt");
    var item =
        store(
            "GRANT",
            id,
            holder.getUsername(),
            items.findById(requestId).orElseThrow().getOwner(),
            "ACTIVE",
            expiry,
            Map.of("bundle", bundle, "maxOpens", 1));
    item.setReferenceId(requestId);
    items.save(item);
    String bundleHash = BridgeProtocol.hash(bundle);
    return Map.of(
        "token",
        token,
        "grantId",
        id,
        "bundle",
        bundle,
        "consentReceipt",
        Map.of(
            "format",
            "foliolet-holder-consent-v1",
            "bundleHash",
            bundleHash,
            "presentation",
            Map.of(
                "requestHash",
                BridgeProtocol.hash(bundle.get("request")),
                "credentialId",
                credentialId,
                "disclosuresHash",
                disclosures((List<?>) bundle.get("claims")),
                "nonce",
                map(bundle.get("request")).get("nonce"),
                "verifier",
                map(bundle.get("request")).get("verifier"),
                "expiresAt",
                expiry),
            "holderSignature",
            bundle.get("holderSignature")),
        "expiresAt",
        expiry);
  }

  @Transactional
  public Map<String, Object> open(String token) {
    String id = Hash.sha3String(token);
    var item = items.lock(id).orElseThrow(() -> new IllegalArgumentException("Unknown share"));
    if (!item.getKind().equals("GRANT")
        || !item.getStatus().equals("ACTIVE")
        || item.getExpiresAt() <= now()
        || item.getOpens() >= 1)
      throw new IllegalArgumentException("Share expired, revoked or already opened");
    item.setOpens(item.getOpens() + 1);
    items.save(item);
    return map(payload(item).get("bundle"));
  }

  public Map<String, Object> grantStatus(String token) {
    var item =
        items
            .findById(Hash.sha3String(token))
            .orElseThrow(() -> new IllegalArgumentException("Unknown share"));
    if (!item.getKind().equals("GRANT")) throw new IllegalArgumentException("Unknown share");
    return Map.of(
        "active",
        item.getStatus().equals("ACTIVE") && item.getExpiresAt() > now() && item.getOpens() < 1,
        "expiresAt",
        item.getExpiresAt(),
        "opens",
        item.getOpens());
  }

  @Transactional
  public void revokeGrant(User holder, String id) {
    var item = owned(id, holder, "GRANT");
    item.setStatus("REVOKED");
    items.save(item);
  }

  public Map<String, Object> evaluate(Map<String, Object> bundle) throws Exception {
    BridgeProtocol.exact(
        bundle,
        "format",
        "registry",
        "chainId",
        "credential",
        "request",
        "requestSignature",
        "claims",
        "holderSignature");
    if (!text(bundle, "format").equals("foliolet-evidence-bridge-v1")
        || !BridgeProtocol.eq(bundle.get("registry"), chain.registry)
        || number(bundle, "chainId") != chain.chainId)
      throw new IllegalArgumentException("Deployment mismatch");
    var c = map(bundle.get("credential"));
    BridgeProtocol.exact(
        c,
        "id",
        "root",
        "documentCommitment",
        "claimType",
        "issuer",
        "holder",
        "leafCount",
        "version",
        "evidenceClass",
        "expiresAt");
    var r = map(bundle.get("request"));
    String requestId = text(r, "id");
    var stored =
        items
            .findById(requestId)
            .orElseThrow(() -> new IllegalArgumentException("Unrecognized verifier challenge"));
    if (!stored.getKind().equals("REQUEST")
        || !BridgeProtocol.stable(payload(stored)).equals(BridgeProtocol.stable(r)))
      throw new IllegalArgumentException("Request tampered");
    var signer = chain.signer(stored.getOwner());
    if (!BridgeProtocol.eq(
        BridgeProtocol.recover(
            BridgeProtocol.request(chain.chainId, chain.registry, r),
            text(bundle, "requestSignature")),
        signer.getAddress())) throw new IllegalArgumentException("Verifier signature differs");
    var claims = (List<?>) bundle.get("claims");
    List<String> requested = (List<String>) r.get("claims");
    if (claims.size() != requested.size() || claims.size() > 8)
      throw new IllegalArgumentException("Exact requested subset required");
    var seen = new HashSet<String>();
    var values = new HashMap<String, String>();
    String type = text(c, "claimType");
    if (!TYPES.containsKey(type)) throw new IllegalArgumentException("Unsupported type");
    for (Object claim : claims) {
      var revealed = map(claim);
      BridgeProtocol.exact(revealed, "leaf", "proof");
      var leafMap = map(revealed.get("leaf"));
      BridgeProtocol.exact(
          leafMap, "path", "label", "type", "value", "derivedFrom", "salt", "index");
      var leaf = BridgeProtocol.JSON.convertValue(leafMap, MerkleTreeService.Leaf.class);
      var spec = TYPES.get(type).get(leaf.path());
      if (spec == null
          || !requested.contains(leaf.path())
          || !seen.add(leaf.path())
          || !spec.equals(List.of(leaf.type(), leaf.label(), leaf.derivedFrom()))
          || !canonical.value(leaf.type(), leaf.value()).equals(leaf.value()))
        throw new IllegalArgumentException("Typed claim semantics differ");
      var proof =
          ((List<?>) revealed.get("proof"))
              .stream()
                  .map(
                      v -> {
                        BridgeProtocol.exact(map(v), "sibling", "side");
                        return BridgeProtocol.JSON.convertValue(v, MerkleTreeService.Step.class);
                      })
                  .toList();
      if (!merkle.verify(leaf, proof, (int) number(c, "leafCount"), text(c, "root")))
        throw new IllegalArgumentException("Merkle proof differs");
      values.put(leaf.path(), leaf.value());
    }
    if (!BridgeProtocol.eq(
        BridgeProtocol.recover(
            BridgeProtocol.presentation(
                chain.chainId, chain.registry, r, text(c, "id"), disclosures(claims)),
            text(bundle, "holderSignature")),
        c.get("holder"))) throw new IllegalArgumentException("Holder signature differs");
    var block = chain.block();
    long n = block.getNumber().longValueExact(), timestamp = block.getTimestamp().longValueExact();
    var record = chain.evidence(text(c, "id"), n);
    var issuer = chain.issuer(text(c, "issuer"), type, n);
    var policy = map(r.get("policy"));
    var ledger = new ArrayList<Map<String, Object>>();
    boolean matches = true;
    for (String key :
        List.of(
            "root",
            "documentCommitment",
            "issuer",
            "holder",
            "leafCount",
            "version",
            "evidenceClass",
            "expiresAt")) matches &= BridgeProtocol.eq(c.get(key), record.get(key));
    matches &= BridgeProtocol.eq(record.get("claimTypeHash"), Hash.sha3String(type));
    check(ledger, "anchor", matches, "Immutable on-chain fields match the exact package");
    check(
        ledger,
        "issuer authority",
        Boolean.TRUE.equals(issuer.get("recognized"))
            && !Boolean.TRUE.equals(issuer.get("suspended"))
            && Boolean.TRUE.equals(issuer.get("scoped")),
        "Recognized, unsuspended and within type scope");
    check(
        ledger,
        "lifecycle",
        number(record, "status") == 1 && number(record, "expiresAt") > now(),
        "Active and unexpired; revocation and supersession block reliance");
    check(
        ledger,
        "request window",
        number(r, "issuedAt") <= now() && now() < number(r, "expiresAt"),
        "Signed nonce and deadline");
    check(
        ledger,
        "evidence policy",
        type.equals(policy.get("claimType"))
            && number(c, "evidenceClass") == 2
            && ((List<?>) policy.get("acceptedIssuers"))
                .stream().anyMatch(x -> BridgeProtocol.eq(x, c.get("issuer"))),
        "Typed recognized issuer evidence");
    boolean predicates = true;
    for (var entry : map(policy.get("requiredValues")).entrySet())
      predicates &= Objects.equals(values.get(entry.getKey()), entry.getValue());
    for (var entry : map(policy.get("minimumValues")).entrySet())
      predicates &=
          new BigDecimal(values.get(entry.getKey()))
                  .compareTo(new BigDecimal(entry.getValue().toString()))
              >= 0;
    check(
        ledger,
        "typed predicates",
        predicates,
        "Only disclosed values; no AI or hidden range proof");
    ledger.add(
        Map.of(
            "requirement",
            "freshness",
            "status",
            timestamp <= now() + 30 && now() - timestamp <= number(policy, "maxReadAgeSeconds")
                ? "PASS"
                : "UNKNOWN",
            "reason",
            "Read age bounded by policy"));
    ledger.add(
        Map.of(
            "requirement",
            "source truth",
            "status",
            "UNKNOWN",
            "reason",
            "Test issuer attestation is not proof of real-world truth"));
    String result =
        ledger.stream().anyMatch(l -> l.get("status").equals("FAIL"))
            ? "FAIL"
            : ledger.stream()
                    .filter(l -> !l.get("requirement").equals("source truth"))
                    .anyMatch(l -> l.get("status").equals("UNKNOWN"))
                ? "UNKNOWN"
                : "PASS";
    var evaluation = new LinkedHashMap<String, Object>();
    evaluation.put("result", result);
    evaluation.put("mode", "current");
    evaluation.put("ledger", ledger);
    evaluation.put("bundleHash", BridgeProtocol.hash(bundle));
    evaluation.put("readBlock", n);
    evaluation.put("blockHash", block.getHash());
    evaluation.put("blockTimestamp", timestamp);
    evaluation.put("anchorBlock", record.get("anchorBlock"));
    evaluation.put(
        "lastChangeBlock",
        Math.max(number(record, "changedBlock"), number(issuer, "changedBlock")));
    evaluation.put("decisionAt", now());
    return evaluation;
  }

  private static void check(
      List<Map<String, Object>> ledger, String requirement, boolean pass, String reason) {
    ledger.add(
        Map.of("requirement", requirement, "status", pass ? "PASS" : "FAIL", "reason", reason));
  }

  @Transactional
  public Map<String, Object> decide(User verifier, Map<String, Object> bundle) throws Exception {
    role(verifier, Role.VERIFIER);
    var r = map(bundle.get("request"));
    String id = text(r, "id");
    var challenge =
        items.lock(id).orElseThrow(() -> new IllegalArgumentException("Unknown challenge"));
    if (!challenge.getOwner().equals(verifier.getUsername())
        || !challenge.getKind().equals("REQUEST")) throw new SecurityException("Wrong verifier");
    String decisionId = "decision:" + id;
    if (!challenge.getStatus().equals("OPEN")) {
      var previous = payload(items.findById(decisionId).orElseThrow());
      if (BridgeProtocol.eq(
          map(previous.get("evaluation")).get("bundleHash"), BridgeProtocol.hash(bundle)))
        return previous;
      throw new IllegalArgumentException("Nonce already consumed");
    }
    var evaluation = evaluate(bundle);
    String hash = BridgeProtocol.hash(evaluation);
    String signature =
        BridgeProtocol.sign(
            BridgeProtocol.decision(
                chain.chainId,
                chain.registry,
                text(evaluation, "bundleHash"),
                hash,
                text(evaluation, "blockHash"),
                number(evaluation, "readBlock")),
            chain.signer(verifier.getUsername()));
    var receipt =
        Map.<String, Object>of(
            "format",
            "foliolet-decision-v1",
            "evaluation",
            evaluation,
            "decisionHash",
            hash,
            "signature",
            signature,
            "verifier",
            r.get("verifier"),
            "bundle",
            bundle);
    store(
        "DECISION",
        decisionId,
        verifier.getUsername(),
        challenge.getRecipient(),
        "RECORDED",
        0,
        receipt);
    challenge.setStatus("CONSUMED");
    items.save(challenge);
    return receipt;
  }
}
