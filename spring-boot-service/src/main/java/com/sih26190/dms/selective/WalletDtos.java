package com.sih26190.dms.selective;

import com.sih26190.dms.selective.MerkleTreeService.RevealedClaim;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.time.Instant;
import java.util.List;

public final class WalletDtos {
  private WalletDtos() {}

  public record ClaimInput(
      @NotBlank @Size(max = 100) String path,
      @NotBlank @Size(max = 100) String label,
      @NotBlank String type,
      @NotBlank @Size(max = 1000) String value) {}

  public record ConfirmClaims(@NotEmpty @Size(max = 64) List<@Valid ClaimInput> claims) {}

  public record ShareRequest(
      @NotBlank String credentialId,
      @NotEmpty @Size(max = 128) List<String> claimIds,
      @NotBlank @Size(max = 150) String verifierLabel,
      @NotBlank @Size(max = 250) String purpose,
      @Min(1) @Max(10080) int expiresInMinutes,
      boolean oneTime) {}

  public record ObservationInput(
      @NotBlank String agentId,
      @NotBlank String itemId,
      @NotBlank @Size(max = 255) String filename,
      @Pattern(regexp = "[0-9a-f]{64}") @NotNull String sha256,
      @NotNull Instant observedAt,
      @Min(1) long sequence,
      @Pattern(regexp = "0x[0-9a-f]{64}") @NotNull String previousDigest,
      @Pattern(regexp = "[0-9a-f]{64}") @NotNull String signature) {}

  public record Provenance(
      String level,
      String explanation,
      Instant firstReceivedAt,
      Instant lastReceivedAt,
      int observations,
      boolean observedChanges,
      boolean enrollmentMatchesFirst,
      String agentId) {}

  public record Anchor(
      String contract,
      long chainId,
      String operator,
      String txHash,
      Instant anchoredAt,
      String documentCommitment,
      String provenanceDigest,
      int provenanceCode) {}

  public record Presentation(
      String grantId,
      String verifierLabel,
      String purpose,
      String nonce,
      Instant createdAt,
      Instant expiresAt,
      boolean oneTime) {}

  public record Bundle(
      String format,
      String credentialId,
      int credentialVersion,
      String merkleRoot,
      int leafCount,
      Anchor anchor,
      Provenance provenance,
      Presentation presentation,
      List<RevealedClaim> claims,
      String envelopeHash,
      String platformSignature) {}

  public record CheckResult(
      boolean proofValid,
      boolean signatureValid,
      boolean anchorMatches,
      boolean current,
      boolean policyActive,
      boolean verified,
      String message) {}

  public record PublicResult(Bundle bundle, CheckResult verification) {}
}
