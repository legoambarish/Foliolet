package com.sih26190.dms.selective;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.sih26190.dms.blockchain.SelectiveDisclosureBlockchainService.ChainAnchor;
import com.sih26190.dms.model.*;
import com.sih26190.dms.repository.UserRepository;
import com.sih26190.dms.selective.WalletDtos.*;
import com.sih26190.dms.selective.repository.*;
import java.time.Instant;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mock.web.MockMultipartFile;

class WalletWorkflowTest extends WalletTestContext {
  @Autowired WalletService wallet;
  @Autowired DisclosureService disclosure;
  @Autowired IntegrityService integrity;
  @Autowired PrivateVault vault;
  @Autowired PresentationSigner signer;
  @Autowired WalletJson json;
  @Autowired UserRepository users;
  @Autowired CredentialClaimRepository claims;
  @Autowired DisclosureGrantRepository grants;
  final Map<String, ChainAnchor> anchors = new HashMap<>();
  User owner, other;

  @BeforeEach
  void setup() throws Exception {
    owner = new User();
    owner.setUsername("holder-" + UUID.randomUUID());
    owner.setPassword("not-used");
    owner.setRole(Role.HOLDER);
    owner = users.save(owner);
    other = new User();
    other.setUsername("other-" + UUID.randomUUID());
    other.setPassword("not-used");
    other.setRole(Role.HOLDER);
    other = users.save(other);
    when(chain.address()).thenReturn("0x" + "11".repeat(20));
    when(chain.chainId()).thenReturn(1337L);
    when(chain.operator()).thenReturn(TEST_CREDENTIALS.getAddress());
    when(chain.get(anyString())).thenAnswer(call -> anchors.get(call.getArgument(0)));
    when(chain.anchor(
            anyString(),
            anyString(),
            anyString(),
            anyString(),
            anyInt(),
            anyInt(),
            nullable(String.class)))
        .thenAnswer(
            call -> {
              anchors.put(
                  call.getArgument(0),
                  new ChainAnchor(
                      call.getArgument(1),
                      call.getArgument(2),
                      call.getArgument(3),
                      chain.operator(),
                      Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS),
                      call.getArgument(4),
                      call.getArgument(5),
                      1,
                      "0x" + "00".repeat(32)));
              return "0x" + "99".repeat(32);
            });
  }

  Map<String, Object> document() {
    var file =
        new MockMultipartFile(
            "file",
            "marksheet.txt",
            "text/plain",
            "Name: Private Student\nCGPA: 9.17\n".getBytes());
    var d = wallet.enroll(file, "Marksheet", "Education", null, null, owner);
    String id = (String) d.get("id");
    wallet.confirm(
        id,
        new ConfirmClaims(
            List.of(
                new ClaimInput("person.name", "Name", "string", "Private Student"),
                new ClaimInput("education.cgpa", "CGPA", "decimal", "9.170"),
                new ClaimInput("person.birth_date", "Date of birth", "date", "2004-01-02"),
                new ClaimInput(
                    "education.institution", "Institution", "string", "Example College"))),
        owner);
    return wallet.anchor(id, owner);
  }

  @Test
  void selectOneDerivedFactAndRejectEveryPolicyFailure() {
    var d = document();
    String id = (String) d.get("id");
    var c =
        claims.findByCredentialIdOrderByLeafIndexAsc(id).stream()
            .filter(x -> x.path.equals("education.cgpa_at_least_8_5"))
            .findFirst()
            .orElseThrow();
    var input =
        new ShareRequest(id, List.of(c.id), "Recruiter", "Internship eligibility", 30, true);
    assertThrows(RuntimeException.class, () -> disclosure.create(input, other));
    assertThrows(RuntimeException.class, () -> wallet.detail(id, other));
    var share = disclosure.create(input, owner);
    String token = ((String) share.get("shareUrl")).split("/verify/")[1].replace("/", "");
    var result = disclosure.open(token);
    assertTrue(result.verification().verified());
    assertEquals(1, result.bundle().claims().size());
    assertEquals("true", result.bundle().claims().get(0).leaf().value());
    assertTrue(signer.verify(result.bundle()));
    String encoded = json.write(result.bundle());
    assertEquals(result.bundle(), json.readBundle(encoded));
    assertThrows(IllegalArgumentException.class,
        () -> json.readBundle(encoded.substring(0, encoded.length()-1) + ",\"unsignedExtra\":true}"));
    assertThrows(IllegalArgumentException.class,
        () -> json.readBundle(encoded.replace("\"oneTime\":true", "\"oneTime\":\"true\"")));
    assertThrows(IllegalArgumentException.class,
        () -> json.readBundle(encoded.replace("\"oneTime\":true", "\"oneTime\":null")));
    assertThrows(IllegalArgumentException.class,
        () -> json.readBundle(encoded.replace("\"chainId\":1337", "\"chainId\":\"1337\"")));
    assertThrows(IllegalArgumentException.class,
        () -> json.readBundle(encoded.replace("\"value\":\"true\"", "\"value\":true")));
    assertThrows(RuntimeException.class, () -> disclosure.open(token));
    disclosure.revoke((String) share.get("id"), owner);
    assertFalse(disclosure.verify(result.bundle(), true).verified());
    var again =
        disclosure.create(new ShareRequest(id, List.of(c.id), "Other", "Purpose", 1, false), owner);
    var grant = grants.findById((String) again.get("id")).orElseThrow();
    grant.expiresAt = Instant.now().minusSeconds(1);
    grants.save(grant);
    assertThrows(
        RuntimeException.class,
        () ->
            disclosure.open(
                ((String) again.get("shareUrl")).split("/verify/")[1].replace("/", "")));
    var anchor = anchors.get(id);
    anchors.put(
        id,
        new ChainAnchor(
            "0x" + "ab".repeat(32),
            anchor.documentCommitment(),
            anchor.provenanceDigest(),
            anchor.owner(),
            anchor.anchoredAt(),
            1,
            0,
            1,
            anchor.supersededBy()));
    assertFalse(disclosure.verify(result.bundle(), false).verified());
  }

  @Test
  void signedProvenanceCannotContradictItsAnchoredCode() {
    String id = (String) document().get("id");
    var claim = claims.findByCredentialIdOrderByLeafIndexAsc(id).get(0);
    var share = disclosure.create(new ShareRequest(id, List.of(claim.id), "Desk", "Eligibility", 30, false), owner);
    var b = disclosure.open(((String) share.get("shareUrl")).split("/verify/")[1].replace("/", "")).bundle();
    var old = b.provenance();
    var provenance = new Provenance("FIRST_SEEN_TRACKED", old.explanation(), old.firstReceivedAt(),
        old.lastReceivedAt(), old.observations(), old.observedChanges(), old.enrollmentMatchesFirst(), old.agentId());
    String digest = PresentationSigner.provenanceHash(provenance);
    var a = b.anchor();
    var changed = new Anchor(a.contract(), a.chainId(), a.operator(), a.txHash(), a.anchoredAt(),
        a.documentCommitment(), digest, 0);
    var onChain = anchors.get(id);
    anchors.put(id, new ChainAnchor(onChain.root(), onChain.documentCommitment(), digest,
        onChain.owner(), onChain.anchoredAt(), onChain.version(), 0, onChain.status(), onChain.supersededBy()));
    var signed = signer.sign(new Bundle(b.format(), b.credentialId(), b.credentialVersion(), b.merkleRoot(),
        b.leafCount(), changed, provenance, b.presentation(), b.claims(), null, null));
    assertTrue(signer.verify(signed));
    assertFalse(disclosure.verify(signed, false).verified());
  }

  @Test
  void invalidStoredProofCannotReleaseOrConsume() {
    var d = document();
    String id = (String) d.get("id");
    var claim = claims.findByCredentialIdOrderByLeafIndexAsc(id).stream()
        .filter(c -> c.path.equals("education.cgpa")).findFirst().orElseThrow();
    var share = disclosure.create(new ShareRequest(id, List.of(claim.id), "Desk", "Eligibility", 30, true), owner);
    var grant = grants.findById((String) share.get("id")).orElseThrow();
    String original = grant.signedBundle;
    String plaintext = vault.open(original, grant.id);
    assertTrue(plaintext.contains("9.17"));
    grant.signedBundle = vault.seal(plaintext.replace("9.17", "8.17"), grant.id);
    grants.save(grant);
    String token = ((String) share.get("shareUrl")).split("/verify/")[1].replace("/", "");
    assertThrows(RuntimeException.class, () -> disclosure.open(token));
    assertEquals(0, grants.findById(grant.id).orElseThrow().views);
    var restored = grants.findById(grant.id).orElseThrow();
    restored.signedBundle = original;
    grants.save(restored);
    assertTrue(disclosure.open(token).verification().verified());
  }

  @Test
  void suggestionsAreTransientAndCustomLabelsKeepTheirOwnMetadata() {
    var d = wallet.enroll(new MockMultipartFile("file", "marks.txt", "text/plain",
        "Name: Private Student\nCGPA: 9.17\n".getBytes()), "Marksheet", "Education", null, null, owner);
    String id = (String) d.get("id");
    assertEquals(2, ((List<?>) wallet.detail(id, owner).get("suggestions")).size());
    var confirmed = wallet.confirm(id, new ConfirmClaims(List.of(
        new ClaimInput("custom.eligibility", "CGPA at least 8.5", "boolean", "true"))), owner);
    assertFalse(confirmed.containsKey("suggestions"));
    var c = claims.findByCredentialIdOrderByLeafIndexAsc(id).get(0);
    assertEquals("custom.eligibility", wallet.leaf(c).path());
    assertEquals("", wallet.leaf(c).derivedFrom());
    wallet.anchor(id, owner);
    var share = disclosure.create(new ShareRequest(id, List.of(c.id), "Desk", "Eligibility", 30, false), owner);
    var released = disclosure.open(((String) share.get("shareUrl")).split("/verify/")[1].replace("/", ""));
    assertEquals("custom.eligibility", released.bundle().claims().get(0).leaf().path());
    assertEquals("", released.bundle().claims().get(0).leaf().derivedFrom());
  }

  @Test
  void encryptedValuesAndAgentAuthentication() {
    var d = document();
    String id = (String) d.get("id");
    for (var c : claims.findByCredentialIdOrderByLeafIndexAsc(id))
      assertFalse(c.encryptedLeaf.contains("Private Student"));
    assertThrows(
        RuntimeException.class,
        () -> vault.open(vault.seal("Private", "first"), "different-context"));
    var pairing = integrity.create(owner, "Laptop");
    var input =
        new ObservationInput(
            (String) pairing.get("agentId"),
            UUID.randomUUID().toString(),
            "file.txt",
            "12".repeat(32),
            Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS),
            1,
            "0x" + "00".repeat(32),
            "00".repeat(32));
    assertThrows(RuntimeException.class, () -> integrity.observe(input));
    var signed =
        new ObservationInput(
            input.agentId(),
            input.itemId(),
            input.filename(),
            input.sha256(),
            input.observedAt(),
            1,
            input.previousDigest(),
            IntegrityService.hmac(
                MerkleTreeService.hex32((String) pairing.get("secret")),
                IntegrityService.message(input)));
    var accepted = integrity.observe(signed);
    assertEquals(accepted, integrity.observe(signed));
    assertThrows(
        RuntimeException.class,
        () ->
            integrity.provenance(other, (String) accepted.get("observationId"), "file".getBytes()));
    integrity.revoke(owner, input.agentId());
    assertThrows(RuntimeException.class, () -> integrity.observe(signed));
  }

  @Test
  void privateFileRecoveryRejectsChangedBackup() throws Exception {
    var d = document();
    String id = (String) d.get("id");
    var row = wallet.owned(id, owner);
    java.nio.file.Files.writeString(java.nio.file.Paths.get(row.filePath), "corrupt");
    var recovered = wallet.verifyFile(id, owner, true);
    assertEquals(true, recovered.get("restored"));
    java.nio.file.Files.writeString(java.nio.file.Paths.get(row.filePath), "corrupt");
    java.nio.file.Files.writeString(java.nio.file.Paths.get(row.backupPath), "corrupt-backup");
    assertEquals(false, wallet.verifyFile(id, owner, true).get("restored"));
  }

  @Test
  void failedAnchorFreezesFactsAndCanBeRetriedWithoutChangingCommitment() throws Exception {
    var d =
        wallet.enroll(
            new MockMultipartFile("file", "sample.txt", "text/plain", "private source".getBytes()),
            "Sample",
            "Other",
            null,
            null,
            owner);
    String id = (String) d.get("id");
    var input =
        new ConfirmClaims(List.of(new ClaimInput("fact.name", "Name", "string", "Private")));
    var confirmed = wallet.confirm(id, input, owner);
    String root = (String) confirmed.get("merkleRoot");
    when(chain.anchor(
            eq(id),
            anyString(),
            anyString(),
            anyString(),
            anyInt(),
            anyInt(),
            nullable(String.class)))
        .thenThrow(new IllegalStateException("isolated test RPC unavailable"))
        .thenAnswer(
            call -> {
              anchors.put(
                  id,
                  new ChainAnchor(
                      call.getArgument(1),
                      call.getArgument(2),
                      call.getArgument(3),
                      chain.operator(),
                      Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS),
                      1,
                      0,
                      1,
                      "0x" + "00".repeat(32)));
              return "0x" + "99".repeat(32);
            });
    assertThrows(RuntimeException.class, () -> wallet.anchor(id, owner));
    assertEquals("ANCHOR_PENDING", wallet.owned(id, owner).status);
    assertThrows(RuntimeException.class, () -> wallet.confirm(id, input, owner));
    var active = wallet.anchor(id, owner);
    assertEquals("ACTIVE", active.get("status"));
    assertEquals(root, active.get("merkleRoot"));
  }
}
