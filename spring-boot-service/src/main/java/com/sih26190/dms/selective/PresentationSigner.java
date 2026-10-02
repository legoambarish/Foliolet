package com.sih26190.dms.selective;

import com.sih26190.dms.selective.WalletDtos.*;
import java.io.*;
import java.util.*;
import org.springframework.stereotype.Component;
import org.web3j.crypto.*;
import org.web3j.utils.Numeric;

@Component
public class PresentationSigner {
  private final Credentials credentials;
  private final MerkleTreeService merkle;

  public PresentationSigner(Credentials credentials, MerkleTreeService merkle) {
    this.credentials = credentials;
    this.merkle = merkle;
  }

  public static String provenanceHash(Provenance p) {
    return Numeric.toHexString(
        Hash.sha3(
            MerkleTreeService.encode(
                "provenance-v1",
                p.level(),
                p.explanation(),
                p.firstReceivedAt() == null
                    ? ""
                    : Long.toString(p.firstReceivedAt().getEpochSecond()),
                p.lastReceivedAt() == null
                    ? ""
                    : Long.toString(p.lastReceivedAt().getEpochSecond()),
                Integer.toString(p.observations()),
                Boolean.toString(p.observedChanges()),
                Boolean.toString(p.enrollmentMatchesFirst()),
                p.agentId() == null ? "" : p.agentId())));
  }

  public String hash(Bundle b) {
    try {
      var out = new ByteArrayOutputStream();
      out.write(3);
      Presentation p = b.presentation();
      Anchor a = b.anchor();
      out.write(
          MerkleTreeService.encode(
              b.format(),
              b.credentialId(),
              Integer.toString(b.credentialVersion()),
              b.merkleRoot(),
              Integer.toString(b.leafCount()),
              a.contract().toLowerCase(Locale.ROOT),
              Long.toString(a.chainId()),
              a.operator().toLowerCase(Locale.ROOT),
              a.documentCommitment(),
              a.provenanceDigest(),
              Integer.toString(a.provenanceCode()),
              Long.toString(a.anchoredAt().getEpochSecond()),
              p.grantId(),
              p.verifierLabel(),
              p.purpose(),
              p.nonce(),
              Long.toString(p.createdAt().getEpochSecond()),
              Long.toString(p.expiresAt().getEpochSecond()),
              Boolean.toString(p.oneTime())));
      for (var claim : b.claims())
        out.write(MerkleTreeService.hex32(merkle.leafHash(claim.leaf())));
      return Numeric.toHexString(Hash.sha3(out.toByteArray()));
    } catch (IOException impossible) {
      throw new IllegalStateException(impossible);
    }
  }

  public Bundle sign(Bundle b) {
    String hash = hash(b);
    var signature =
        Sign.signPrefixedMessage(MerkleTreeService.hex32(hash), credentials.getEcKeyPair());
    byte[] bytes = new byte[65];
    System.arraycopy(signature.getR(), 0, bytes, 0, 32);
    System.arraycopy(signature.getS(), 0, bytes, 32, 32);
    bytes[64] = signature.getV()[0];
    return new Bundle(
        b.format(),
        b.credentialId(),
        b.credentialVersion(),
        b.merkleRoot(),
        b.leafCount(),
        b.anchor(),
        b.provenance(),
        b.presentation(),
        b.claims(),
        hash,
        Numeric.toHexString(bytes));
  }

  public boolean verify(Bundle b) {
    try {
      String computed = hash(b);
      if (!computed.equals(b.envelopeHash())
          || !provenanceHash(b.provenance()).equals(b.anchor().provenanceDigest())) return false;
      byte[] bytes = Numeric.hexStringToByteArray(b.platformSignature());
      if (bytes.length != 65) return false;
      var signature =
          new Sign.SignatureData(
              bytes[64], Arrays.copyOfRange(bytes, 0, 32), Arrays.copyOfRange(bytes, 32, 64));
      String recovered =
          "0x"
              + Keys.getAddress(
                  Sign.signedPrefixedMessageToKey(MerkleTreeService.hex32(computed), signature));
      return recovered.equalsIgnoreCase(b.anchor().operator());
    } catch (Exception e) {
      return false;
    }
  }
}
