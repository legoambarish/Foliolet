package com.sih26190.dms.selective;

import com.sih26190.dms.blockchain.SelectiveDisclosureBlockchainService;
import com.sih26190.dms.model.User;
import com.sih26190.dms.repository.UserRepository;
import com.sih26190.dms.selective.MerkleTreeService.*;
import com.sih26190.dms.selective.WalletDtos.*;
import com.sih26190.dms.selective.model.*;
import com.sih26190.dms.selective.repository.*;
import com.sih26190.dms.service.AuditService;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class DisclosureService {
  private final DisclosureGrantRepository grants;
  private final DisclosureReceiptRepository receipts;
  private final CredentialDocumentRepository documents;
  private final UserRepository users;
  private final WalletService wallet;
  private final MerkleTreeService merkle;
  private final PresentationSigner signer;
  private final SelectiveDisclosureBlockchainService chain;
  private final ClaimCanonicalizer canonical;
  private final WalletJson json;
  private final PrivateVault vault;
  private final AuditService audit;
  private final String shareBase;

  public DisclosureService(
      DisclosureGrantRepository grants,
      DisclosureReceiptRepository receipts,
      CredentialDocumentRepository documents,
      UserRepository users,
      WalletService wallet,
      MerkleTreeService merkle,
      PresentationSigner signer,
      SelectiveDisclosureBlockchainService chain,
      ClaimCanonicalizer canonical,
      WalletJson json,
      PrivateVault vault,
      AuditService audit,
      @Value("${wallet.share-base-url:http://localhost:8000}") String shareBase) {
    this.grants = grants;
    this.receipts = receipts;
    this.documents = documents;
    this.users = users;
    this.wallet = wallet;
    this.merkle = merkle;
    this.signer = signer;
    this.chain = chain;
    this.canonical = canonical;
    this.json = json;
    this.vault = vault;
    this.audit = audit;
    this.shareBase = shareBase.replaceAll("/$", "");
  }

  @Transactional
  public Map<String, Object> create(ShareRequest request, User owner) {
    var d =
        documents
            .locked(request.credentialId())
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
    if (!d.ownerId.equals(owner.getId())) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
    var onChain = wallet.requireCurrent(d);
    try {
      String current =
          org.web3j.utils.Numeric.toHexString(
              org.web3j.crypto.Hash.sha3(vault.read(d.filePath, d.id)));
      if (!PrivateVault.commitment(d.documentSalt, current).equals(d.documentCommitment))
        throw new IllegalStateException("Changed file");
    } catch (Exception e) {
      throw new ResponseStatusException(
          HttpStatus.CONFLICT, "Run integrity recovery before sharing a changed or missing file");
    }
    var all = wallet.claimRecords(d.id);
    var selected = new HashSet<>(request.claimIds());
    if (selected.isEmpty()
        || selected.size() != request.claimIds().size()
        || selected.size() > all.size())
      throw new IllegalArgumentException("Select distinct facts from this document");
    var leaves = all.stream().map(wallet::leaf).toList();
    var disclosed = new ArrayList<RevealedClaim>();
    for (var c : all)
      if (selected.remove(c.id))
        disclosed.add(new RevealedClaim(wallet.leaf(c), merkle.proof(leaves, c.leafIndex)));
    if (!selected.isEmpty())
      throw new IllegalArgumentException("Selected fact does not belong to this document");
    var grant = new DisclosureGrant();
    grant.id = UUID.randomUUID().toString();
    grant.ownerId = owner.getId();
    grant.credentialId = d.id;
    String token = merkle.randomHex().substring(2);
    grant.tokenHash = PrivateVault.sha256(token.getBytes(StandardCharsets.UTF_8));
    grant.verifierLabel = canonical.text(request.verifierLabel(), 150);
    grant.purpose = canonical.text(request.purpose(), 250);
    grant.nonce = merkle.randomHex();
    grant.createdAt = Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS);
    grant.expiresAt = grant.createdAt.plusSeconds(request.expiresInMinutes() * 60L);
    grant.oneTime = request.oneTime();
    grant.selectedIds = json.write(request.claimIds());
    var anchor =
        new Anchor(
            d.contractAddress,
            d.chainId,
            chain.operator(),
            d.anchorTx,
            onChain.anchoredAt(),
            d.documentCommitment,
            d.provenanceDigest,
            onChain.provenanceLevel());
    var presentation =
        new Presentation(
            grant.id,
            grant.verifierLabel,
            grant.purpose,
            grant.nonce,
            grant.createdAt,
            grant.expiresAt,
            grant.oneTime);
    var bundle =
        signer.sign(
            new Bundle(
                MerkleTreeService.FORMAT,
                d.id,
                d.version,
                d.merkleRoot,
                all.size(),
                anchor,
                json.read(d.provenanceJson, Provenance.class),
                presentation,
                disclosed,
                null,
                null));
    grant.signedBundle = vault.seal(json.write(bundle), grant.id);
    grants.save(grant);
    audit.logWallet(owner, d.id, grant.id, "DISCLOSURE_CREATED");
    return Map.of(
        "id",
        grant.id,
        "shareUrl",
        shareBase + "/verify/" + token + "/",
        "expiresAt",
        grant.expiresAt,
        "disclosedCount",
        disclosed.size(),
        "privateCount",
        all.size() - disclosed.size());
  }

  private String policy(DisclosureGrant g, boolean enforceViews) {
    if (g.revokedAt != null) return "REVOKED";
    if (!g.expiresAt.isAfter(Instant.now())) return "EXPIRED";
    if (enforceViews && g.oneTime && g.views > 0) return "CONSUMED";
    return "ACTIVE";
  }

  public Map<String, Object> status(String id) {
    var g =
        grants.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
    String state = policy(g, true);
    var document = documents.findById(g.credentialId);
    if (document.isEmpty() || !document.get().status.equals("ACTIVE"))
      state = "CREDENTIAL_UNAVAILABLE";
    return Map.of(
        "status", state, "expiresAt", g.expiresAt, "oneTime", g.oneTime, "views", g.views);
  }

  public List<Map<String, Object>> list(User owner) {
    return grants.findByOwnerIdOrderByCreatedAtDesc(owner.getId()).stream()
        .map(
            g -> {
              Map<String, Object> m = new LinkedHashMap<>();
              m.put("id", g.id);
              m.put("credentialId", g.credentialId);
              m.put("verifierLabel", g.verifierLabel);
              m.put("purpose", g.purpose);
              m.put("expiresAt", g.expiresAt);
              m.put("createdAt", g.createdAt);
              m.put("status", status(g.id).get("status"));
              m.put("views", g.views);
              m.put("oneTime", g.oneTime);
              m.put(
                  "receipts",
                  receipts.findByGrantIdOrderByVerifiedAtDesc(g.id).stream()
                      .map(r -> Map.of("verifiedAt", r.verifiedAt, "result", r.result))
                      .toList());
              return m;
            })
        .toList();
  }

  @Transactional
  public void revoke(String id, User owner) {
    var g = grants.locked(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
    if (!g.ownerId.equals(owner.getId())) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
    g.revokedAt = Instant.now();
    grants.save(g);
    audit.logWallet(owner, g.credentialId, id, "DISCLOSURE_REVOKED");
  }

  @Transactional
  public PublicResult open(String token) {
    if (!token.matches("[0-9a-f]{64}"))
      throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Proof link not found");
    var g =
        grants
            .byTokenLocked(PrivateVault.sha256(token.getBytes(StandardCharsets.UTF_8)))
            .orElseThrow(
                () -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Proof link not found"));
    String state = policy(g, true);
    if (!state.equals("ACTIVE"))
      throw new ResponseStatusException(
          HttpStatus.GONE, "Proof link is " + state.toLowerCase(Locale.ROOT));
    var bundle = json.read(vault.open(g.signedBundle, g.id), Bundle.class);
    CheckResult checked = verify(bundle, false);
    if (!checked.verified())
      throw new ResponseStatusException(HttpStatus.CONFLICT, checked.message());
    g.views++;
    grants.save(g);
    var receipt = new DisclosureReceipt();
    receipt.id = UUID.randomUUID().toString();
    receipt.grantId = g.id;
    receipt.verifiedAt = Instant.now();
    receipt.result = "VERIFIED_RELEASE";
    receipts.save(receipt);
    audit.logWallet(
        users.findById(g.ownerId).orElseThrow(), g.credentialId, g.id, "PUBLIC_PROOF_RELEASED");
    return new PublicResult(bundle, checked);
  }

  public CheckResult verify(Bundle b, boolean checkServicePolicy) {
    boolean proof = false, signature = false, anchor = false, current = false, policyActive = false;
    try {
      if (!MerkleTreeService.FORMAT.equals(b.format())
          || b.claims() == null
          || b.claims().isEmpty()
          || b.claims().size() > 128)
        throw new IllegalArgumentException("Unsupported or empty proof");
      var indices = new HashSet<Integer>();
      var paths = new HashSet<String>();
      proof = true;
      for (var c : b.claims()) {
        Leaf l = c.leaf();
        if (!indices.add(l.index())
            || !paths.add(l.path())
            || !canonical.path(l.path()).equals(l.path())
            || !canonical.text(l.label(), 100).equals(l.label())
            || !canonical.value(l.type(), l.value()).equals(l.value())
            || !merkle.verify(l, c.proof(), b.leafCount(), b.merkleRoot())) proof = false;
      }
      signature = signer.verify(b);
      if (!proof || !signature)
        return new CheckResult(
            proof,
            signature,
            false,
            false,
            false,
            false,
            "Proof or signed presentation was modified");
      var a = b.anchor();
      int provenanceCode = switch (b.provenance().level()) {
        case "SELF_ENROLLED" -> 0;
        case "FIRST_SEEN_TRACKED" -> 1;
        default -> -1;
      };
      if (provenanceCode < 0 || a.provenanceCode() != provenanceCode)
        throw new IllegalArgumentException("Inconsistent source assurance");
      if (a.chainId() != chain.chainId()
          || !a.contract().equalsIgnoreCase(chain.address())
          || !a.operator().equalsIgnoreCase(chain.operator()))
        return new CheckResult(
            true,
            true,
            false,
            false,
            false,
            false,
            "Unexpected network, registry or platform signer");
      var c = chain.get(b.credentialId());
      anchor =
          c.root().equals(b.merkleRoot())
              && c.documentCommitment().equals(a.documentCommitment())
              && c.provenanceDigest().equals(a.provenanceDigest())
              && c.version() == b.credentialVersion()
              && c.provenanceLevel() == a.provenanceCode()
              && c.owner().equalsIgnoreCase(a.operator())
              && c.anchoredAt().equals(a.anchoredAt());
      current = c.status() == 1;
      Instant now = Instant.now();
      var p = b.presentation();
      policyActive =
          p.expiresAt().isAfter(now)
              && p.createdAt().isBefore(now.plusSeconds(30))
              && p.expiresAt().isAfter(p.createdAt())
              && !p.expiresAt().isAfter(p.createdAt().plusSeconds(604800));
      if (checkServicePolicy) {
        var grant = grants.findById(p.grantId());
        policyActive =
            policyActive
                && grant.isPresent()
                && policy(grant.get(), false).equals("ACTIVE")
                && signer
                    .hash(
                        json.read(
                            vault.open(grant.get().signedBundle, grant.get().id), Bundle.class))
                    .equals(b.envelopeHash());
      }
      boolean verified = proof && signature && anchor && current && policyActive;
      return new CheckResult(
          proof,
          signature,
          anchor,
          current,
          policyActive,
          verified,
          verified
              ? "Disclosed facts match an active anchored commitment. Source assurance is shown"
                    + " separately."
              : "Anchor, credential freshness or disclosure policy did not pass");
    } catch (Exception e) {
      return new CheckResult(
          proof,
          signature,
          anchor,
          current,
          policyActive,
          false,
          "Verification could not complete; proof is not accepted");
    }
  }
}
