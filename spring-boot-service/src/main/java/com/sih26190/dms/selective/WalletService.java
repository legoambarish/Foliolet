package com.sih26190.dms.selective;

import com.sih26190.dms.blockchain.SelectiveDisclosureBlockchainService;
import com.sih26190.dms.model.User;
import com.sih26190.dms.selective.MerkleTreeService.*;
import com.sih26190.dms.selective.WalletDtos.*;
import com.sih26190.dms.selective.model.*;
import com.sih26190.dms.selective.repository.*;
import com.sih26190.dms.service.*;
import java.math.BigDecimal;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.regex.*;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import org.web3j.crypto.Hash;
import org.web3j.utils.Numeric;

@Service
public class WalletService {
  private final CredentialDocumentRepository documents;
  private final CredentialClaimRepository claims;
  private final PrivateVault vault;
  private final MerkleTreeService merkle;
  private final ClaimCanonicalizer canonical;
  private final IntegrityService integrity;
  private final WalletJson json;
  private final SelectiveDisclosureBlockchainService chain;
  private final TextExtractionService extraction;
  private final AuditService audit;
  private final TransactionTemplate tx;

  public WalletService(
      CredentialDocumentRepository documents,
      CredentialClaimRepository claims,
      PrivateVault vault,
      MerkleTreeService merkle,
      ClaimCanonicalizer canonical,
      IntegrityService integrity,
      WalletJson json,
      SelectiveDisclosureBlockchainService chain,
      TextExtractionService extraction,
      AuditService audit,
      org.springframework.transaction.PlatformTransactionManager manager) {
    this.documents = documents;
    this.claims = claims;
    this.vault = vault;
    this.merkle = merkle;
    this.canonical = canonical;
    this.integrity = integrity;
    this.json = json;
    this.chain = chain;
    this.extraction = extraction;
    this.audit = audit;
    tx = new TransactionTemplate(manager);
  }

  public CredentialDocument owned(String id, User user) {
    var d =
        documents
            .findById(id)
            .orElseThrow(
                () -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Document not found"));
    requireOwner(d, user);
    return d;
  }

  private void requireOwner(CredentialDocument d, User user) {
    if (!d.ownerId.equals(user.getId()))
      throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Document not found");
  }

  private CredentialDocument locked(String id, User user) {
    var d =
        documents
            .locked(id)
            .orElseThrow(
                () -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Document not found"));
    requireOwner(d, user);
    return d;
  }

  public Map<String, Object> enroll(
      MultipartFile file,
      String name,
      String category,
      String observationId,
      String previousId,
      User owner) {
    if (file.isEmpty() || file.getSize() > 20 * 1024 * 1024)
      throw new IllegalArgumentException("Use a nonempty file up to 20 MB");
    String display = canonical.text(name, 150);
    String normalizedCategory = canonical.text(category, 30);
    if (!Set.of("Education", "Employment", "Finance", "Identity", "Purchase", "Other")
        .contains(normalizedCategory)) throw new IllegalArgumentException("Unsupported category");
    byte[] bytes;
    try {
      bytes = file.getBytes();
    } catch (Exception e) {
      throw new IllegalArgumentException("Cannot read upload");
    }
    var provenance = integrity.provenance(owner, observationId, bytes);
    var d = new CredentialDocument();
    d.id = merkle.randomHex();
    d.logicalId = UUID.randomUUID().toString();
    d.version = 1;
    if (previousId != null && !previousId.isBlank()) {
      CredentialDocument previous = owned(previousId, owner);
      if (!previous.status.equals("ACTIVE"))
        throw new IllegalArgumentException("Replace an active version");
      requireCurrent(previous);
      d.logicalId = previous.logicalId;
      d.version = previous.version + 1;
      d.previousId = previous.id;
    }
    d.ownerId = owner.getId();
    d.displayName = display;
    d.category = normalizedCategory;
    String original = file.getOriginalFilename();
    d.originalFilename =
        original == null
            ? "document"
            : original
                .replace('\\', '/')
                .substring(original.replace('\\', '/').lastIndexOf('/') + 1);
    d.documentHash = Numeric.toHexString(Hash.sha3(bytes));
    d.documentSalt = merkle.randomHex();
    d.documentCommitment = PrivateVault.commitment(d.documentSalt, d.documentHash);
    d.provenanceLevel = provenance.level();
    d.provenanceJson = json.write(provenance);
    d.provenanceDigest = PresentationSigner.provenanceHash(provenance);
    d.status = "DRAFT";
    d.createdAt = Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS);
    try {
      d.filePath = vault.store(d.id, bytes).toString();
      d.backupPath = vault.backup(d.id).toString();
    } catch (Exception e) {
      throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Private storage failed");
    }
    tx.executeWithoutResult(
        status -> {
          documents.save(d);
          audit.logWallet(owner, d.id, null, "DOCUMENT_ENROLLED");
        });
    return detail(d, owner);
  }

  private List<ClaimInput> suggest(byte[] bytes, String filename) {
    // Deterministic convenience suggestions, never an authenticity source. No external AI calls.
    var result = new ArrayList<ClaimInput>();
    try {
      String text = extraction.extractBytes(bytes, filename);
      for (String[] mapping :
          List.of(
              new String[] {"CGPA", "education.cgpa", "CGPA", "decimal"},
              new String[] {"Name", "person.name", "Full name", "string"},
              new String[] {"Institution", "education.institution", "Institution", "string"},
              new String[] {"Course", "education.course", "Course", "string"},
              new String[] {"Date of birth", "person.birth_date", "Date of birth", "date"},
              new String[] {"Purchase date", "purchase.date", "Purchase date", "date"},
              new String[] {
                "Product identifier", "purchase.product_id", "Product identifier", "string"
              })) {
        Matcher m =
            Pattern.compile("(?im)^\\s*" + Pattern.quote(mapping[0]) + "\\s*[:=]\\s*([^\\r\\n]+)")
                .matcher(text);
        if (m.find()) {
          try {
            result.add(
                new ClaimInput(
                    mapping[1], mapping[2], mapping[3], canonical.value(mapping[3], m.group(1))));
          } catch (RuntimeException ignored) {
          }
        }
      }
    } catch (Exception ignored) {
    } // Scans/binary formats support manual holder confirmation.
    return result;
  }

  public List<Map<String, Object>> list(User user) {
    return documents.findByOwnerIdOrderByCreatedAtDesc(user.getId()).stream()
        .map(d -> summary(d))
        .toList();
  }

  private Map<String, Object> summary(CredentialDocument d) {
    var m = new LinkedHashMap<String, Object>();
    m.put("id", d.id);
    m.put("logicalId", d.logicalId);
    m.put("displayName", d.displayName);
    m.put("category", d.category);
    m.put("version", d.version);
    m.put("status", d.status);
    m.put("createdAt", d.createdAt);
    m.put("anchoredAt", d.anchoredAt);
    m.put("provenanceLevel", d.provenanceLevel);
    m.put("claimCount", claims.findByCredentialIdOrderByLeafIndexAsc(d.id).size());
    m.put("supersededBy", d.supersededBy);
    m.put("previousId", d.previousId);
    return m;
  }

  public Map<String, Object> detail(String id, User owner) {
    return detail(owned(id, owner), owner);
  }

  private Map<String, Object> detail(CredentialDocument d, User owner) {
    var m = summary(d);
    m.put("provenance", json.read(d.provenanceJson, Provenance.class));
    m.put("merkleRoot", d.merkleRoot);
    m.put("anchorTx", d.anchorTx);
    m.put("contract", d.contractAddress);
    m.put("chainId", d.chainId);
    m.put(
        "claims",
        claims.findByCredentialIdOrderByLeafIndexAsc(d.id).stream()
            .map(
                c -> {
                  Leaf leaf = leaf(c);
                  return Map.of(
                      "id",
                      c.id,
                      "path",
                      leaf.path(),
                      "label",
                      leaf.label(),
                      "type",
                      leaf.type(),
                      "value",
                      leaf.value(),
                      "derived",
                      !leaf.derivedFrom().isEmpty(),
                      "derivedFrom",
                      leaf.derivedFrom());
                })
            .toList());
    if (d.status.equals("DRAFT") && ((List<?>) m.get("claims")).isEmpty()) {
      // Suggestions are transient: the encrypted original remains the only retained source.
      try {
        m.put("suggestions", suggest(vault.read(d.filePath, d.id), d.originalFilename));
      } catch (Exception e) {
        throw new ResponseStatusException(HttpStatus.CONFLICT, "Private source unavailable");
      }
    }
    return m;
  }

  public Leaf leaf(CredentialClaim c) {
    return json.read(vault.open(c.encryptedLeaf, c.id), Leaf.class);
  }

  public List<CredentialClaim> claimRecords(String id) {
    return claims.findByCredentialIdOrderByLeafIndexAsc(id);
  }

  public Map<String, Object> confirm(String id, ConfirmClaims input, User owner) {
    return tx.execute(
        status -> {
          var d = locked(id, owner);
          if (!d.status.equals("DRAFT"))
            throw new IllegalArgumentException(
                "Committed or pending facts are immutable; create a new version");
          var entries = new TreeMap<String, ClaimInput>();
          for (var c : input.claims()) {
            String path = canonical.path(c.path());
            if (path.endsWith(".cgpa_at_least_8_5"))
              throw new IllegalArgumentException("Threshold claims are generated by the platform");
            var normalized =
                new ClaimInput(
                    path,
                    canonical.text(c.label(), 100),
                    c.type(),
                    canonical.value(c.type(), c.value()));
            if (entries.put(path, normalized) != null)
              throw new IllegalArgumentException("Duplicate fact path");
          }
          ClaimInput cgpa = entries.get("education.cgpa");
          if (cgpa != null) {
            if (!cgpa.type().equals("decimal"))
              throw new IllegalArgumentException("CGPA must be a decimal");
            BigDecimal v = new BigDecimal(cgpa.value());
            if (v.signum() < 0 || v.compareTo(BigDecimal.TEN) > 0)
              throw new IllegalArgumentException("CGPA must be between 0 and 10");
            entries.put(
                "education.cgpa_at_least_8_5",
                new ClaimInput(
                    "education.cgpa_at_least_8_5",
                    "CGPA at least 8.5",
                    "boolean",
                    Boolean.toString(v.compareTo(new BigDecimal("8.5")) >= 0)));
          }
          claims.deleteByCredentialId(id);
          var leaves = new ArrayList<Leaf>();
          for (var c : entries.values()) {
            String derived = c.path().equals("education.cgpa_at_least_8_5") ? "education.cgpa" : "";
            Leaf leaf =
                new Leaf(
                    c.path(),
                    c.label(),
                    c.type(),
                    c.value(),
                    derived,
                    merkle.randomHex(),
                    leaves.size());
            leaves.add(leaf);
            var row = new CredentialClaim();
            row.id = UUID.randomUUID().toString();
            row.credentialId = id;
            row.leafIndex = leaf.index();
            row.path = leaf.path();
            row.label = leaf.label();
            row.type = leaf.type();
            row.derivedFrom = derived;
            row.encryptedLeaf = vault.seal(json.write(leaf), row.id);
            row.leafHash = merkle.leafHash(leaf);
            claims.save(row);
          }
          d.merkleRoot = merkle.root(leaves);
          documents.save(d);
          audit.logWallet(owner, id, null, "FACTS_CONFIRMED");
          return detail(d, owner);
        });
  }

  public Map<String, Object> anchor(String id, User owner) {
    // Commit pending state before broadcasting: a mined transaction cannot be rolled back with SQL.
    var pending =
        tx.execute(
            status -> {
              var d = locked(id, owner);
              if (d.status.equals("ACTIVE")) {
                requireCurrent(d);
                return d;
              }
              if (!Set.of("DRAFT", "ANCHOR_PENDING").contains(d.status) || d.merkleRoot == null)
                throw new IllegalArgumentException("Confirm facts before anchoring");
              d.status = "ANCHOR_PENDING";
              d.contractAddress = chain.address();
              d.chainId = chain.chainId();
              documents.save(d);
              return d;
            });
    if (pending.status.equals("ACTIVE")) return detail(id, owner);
    try {
      String txHash =
          chain.anchor(
              id,
              pending.merkleRoot,
              pending.documentCommitment,
              pending.provenanceDigest,
              pending.version,
              pending.provenanceLevel.equals("FIRST_SEEN_TRACKED") ? 1 : 0,
              pending.previousId);
      var onChain = chain.get(id);
      return tx.execute(
          status -> {
            var d = locked(id, owner);
            d.status = "ACTIVE";
            if (txHash != null) d.anchorTx = txHash;
            d.anchoredAt = onChain.anchoredAt();
            documents.save(d);
            if (d.previousId != null) {
              var previous = locked(d.previousId, owner);
              previous.status = "SUPERSEDED";
              previous.supersededBy = id;
              documents.save(previous);
            }
            audit.logWallet(owner, id, null, "CREDENTIAL_ANCHORED");
            return detail(d, owner);
          });
    } catch (Exception e) {
      throw new ResponseStatusException(
          HttpStatus.SERVICE_UNAVAILABLE,
          "Anchor not completed; immutable pending version can be retried",
          e);
    }
  }

  public SelectiveDisclosureBlockchainService.ChainAnchor requireCurrent(CredentialDocument d) {
    try {
      if (!d.status.equals("ACTIVE"))
        throw new IllegalArgumentException("Credential is not active");
      if (!chain.address().equalsIgnoreCase(d.contractAddress) || chain.chainId() != d.chainId)
        throw new IllegalStateException("Credential belongs to another configured registry");
      var c = chain.get(d.id);
      if (c.status() != 1
          || !c.root().equals(d.merkleRoot)
          || !c.documentCommitment().equals(d.documentCommitment)
          || !c.provenanceDigest().equals(d.provenanceDigest)
          || c.version() != d.version
          || !c.owner().equalsIgnoreCase(chain.operator())
          || c.provenanceLevel() != (d.provenanceLevel.equals("FIRST_SEEN_TRACKED") ? 1 : 0))
        throw new IllegalArgumentException(
            "Credential root or state does not match the active chain anchor");
      return c;
    } catch (IllegalArgumentException e) {
      throw e;
    } catch (Exception e) {
      throw new ResponseStatusException(
          HttpStatus.SERVICE_UNAVAILABLE, "Chain verification unavailable", e);
    }
  }

  public void revoke(String id, User owner) {
    var d = owned(id, owner);
    if (d.status.equals("REVOKED")) return;
    if (!d.status.equals("ACTIVE"))
      throw new IllegalArgumentException("Only an active credential can be revoked");
    try {
      chain.revoke(id);
    } catch (Exception e) {
      throw new ResponseStatusException(
          HttpStatus.SERVICE_UNAVAILABLE, "Chain revocation not completed; retry", e);
    }
    tx.executeWithoutResult(
        status -> {
          var row = locked(id, owner);
          row.status = "REVOKED";
          documents.save(row);
          audit.logWallet(owner, id, null, "CREDENTIAL_REVOKED");
        });
  }

  public Map<String, Object> verifyFile(String id, User owner, boolean restore) {
    var d = owned(id, owner);
    requireCurrent(d);
    boolean intact = false, restored = false;
    try {
      intact =
          PrivateVault.commitment(
                  d.documentSalt, Numeric.toHexString(Hash.sha3(vault.read(d.filePath, id))))
              .equals(d.documentCommitment);
    } catch (Exception ignored) {
    }
    if (!intact && restore) {
      try {
        byte[] backup = vault.read(d.backupPath, id);
        if (!PrivateVault.commitment(d.documentSalt, Numeric.toHexString(Hash.sha3(backup)))
            .equals(d.documentCommitment)) throw new IllegalStateException("Backup mismatch");
        Files.copy(
            Paths.get(d.backupPath), Paths.get(d.filePath), StandardCopyOption.REPLACE_EXISTING);
        restored = true;
      } catch (Exception ignored) {
      }
    }
    final boolean recovered = restored;
    final boolean matches = intact;
    tx.executeWithoutResult(
        status -> {
          audit.logWallet(
              owner, id, null, matches ? "FILE_INTEGRITY_CHECKED" : "FILE_INTEGRITY_MISMATCH");
          if (recovered) audit.logWallet(owner, id, null, "INTEGRITY_RESTORED");
        });
    return Map.of(
        "intact",
        intact,
        "restored",
        restored,
        "message",
        intact
            ? "Private file matches its anchored commitment."
            : restored
                ? "Changed file detected and restored from a cryptographically checked backup."
                : "Private file is missing or changed. No verified recovery was performed.");
  }

  public Map<String, Object> download(String id, User owner) {
    var d = owned(id, owner); // Private holder-only original. Never used by the public verifier.
    try {
      return Map.of("bytes", vault.read(d.filePath, id), "filename", d.originalFilename);
    } catch (Exception e) {
      throw new ResponseStatusException(
          HttpStatus.CONFLICT, "Private file unavailable or changed; run integrity check");
    }
  }
}
