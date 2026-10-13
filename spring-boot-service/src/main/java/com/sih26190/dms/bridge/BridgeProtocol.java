package com.sih26190.dms.bridge;

import com.fasterxml.jackson.databind.*;
import java.math.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.web3j.crypto.*;
import org.web3j.utils.Numeric;

public final class BridgeProtocol {
  public static final ObjectMapper JSON =
      new ObjectMapper()
          .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
          .enable(com.fasterxml.jackson.core.JsonParser.Feature.STRICT_DUPLICATE_DETECTION);

  private BridgeProtocol() {}

  public static Object sorted(Object v) {
    if (v instanceof Map<?, ?> m) {
      var out = new TreeMap<String, Object>();
      m.forEach((k, x) -> out.put(k.toString(), sorted(x)));
      return out;
    }
    if (v instanceof List<?> l) return l.stream().map(BridgeProtocol::sorted).toList();
    return v;
  }

  public static String stable(Object v) {
    try {
      return JSON.writeValueAsString(sorted(v));
    } catch (Exception e) {
      throw new IllegalArgumentException("Invalid protocol data", e);
    }
  }

  public static Map<String, Object> parse(String text) {
    try {
      return JSON.readValue(
          text, new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {});
    } catch (Exception e) {
      throw new IllegalArgumentException("Invalid JSON package", e);
    }
  }

  public static String hash(Object v) {
    return Hash.sha3String(stable(v));
  }

  public static byte[] word(String hex) {
    return Numeric.toBytesPadded(new BigInteger(Numeric.cleanHexPrefix(hex), 16), 32);
  }

  public static byte[] number(long n) {
    return Numeric.toBytesPadded(BigInteger.valueOf(n), 32);
  }

  public static byte[] concat(byte[]... arrays) {
    int length = Arrays.stream(arrays).mapToInt(a -> a.length).sum();
    byte[] result = new byte[length];
    int i = 0;
    for (byte[] a : arrays) {
      System.arraycopy(a, 0, result, i, a.length);
      i += a.length;
    }
    return result;
  }

  public static byte[] type(String text) {
    return Hash.sha3(text.getBytes(StandardCharsets.UTF_8));
  }

  public static byte[] domain(long chainId, String registry) {
    return Hash.sha3(
        concat(
            type(
                "EIP712Domain(string name,string version,uint256 chainId,address"
                    + " verifyingContract)"),
            type("FolioletEvidenceBridge"),
            type("1"),
            number(chainId),
            word(registry)));
  }

  public static byte[] typed(long chainId, String registry, byte[] structure) {
    return Hash.sha3(
        concat(new byte[] {0x19, 0x01}, domain(chainId, registry), Hash.sha3(structure)));
  }

  public static byte[] request(long chainId, String registry, Map<String, Object> request) {
    return typed(
        chainId, registry, concat(type("Request(bytes32 requestHash)"), word(hash(request))));
  }

  public static byte[] presentation(
      long chainId, String registry, Map<String, Object> request, String id, String disclosures) {
    return typed(
        chainId,
        registry,
        concat(
            type(
                "Presentation(bytes32 requestHash,bytes32 credentialId,bytes32"
                    + " disclosuresHash,bytes32 nonce,address verifier,uint64 expiresAt)"),
            word(hash(request)),
            word(id),
            word(disclosures),
            word(request.get("nonce").toString()),
            word(request.get("verifier").toString()),
            number(((Number) request.get("expiresAt")).longValue())));
  }

  public static byte[] decision(
      long chainId,
      String registry,
      String bundleHash,
      String decisionHash,
      String blockHash,
      long readBlock) {
    return typed(
        chainId,
        registry,
        concat(
            type(
                "Decision(bytes32 bundleHash,bytes32 decisionHash,bytes32 blockHash,uint64"
                    + " readBlock)"),
            word(bundleHash),
            word(decisionHash),
            word(blockHash),
            number(readBlock)));
  }

  public static String sign(byte[] hash, Credentials signer) {
    var s = Sign.signMessage(hash, signer.getEcKeyPair(), false);
    return Numeric.toHexString(concat(s.getR(), s.getS(), s.getV()));
  }

  public static String recover(byte[] hash, String signature) {
    try {
      if (signature == null || !signature.matches("0x[0-9a-fA-F]{130}"))
        throw new IllegalArgumentException();
      byte[] bytes = Numeric.hexStringToByteArray(signature);
      byte v = bytes[64];
      if (v != 27 && v != 28) throw new IllegalArgumentException();
      var s = new BigInteger(1, Arrays.copyOfRange(bytes, 32, 64));
      if (s.signum() == 0
          || s.compareTo(
                  new BigInteger(
                          "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)
                      .shiftRight(1))
              > 0) throw new IllegalArgumentException();
      return "0x"
          + Keys.getAddress(
              Sign.signedMessageHashToKey(
                  hash,
                  new Sign.SignatureData(
                      v, Arrays.copyOfRange(bytes, 0, 32), Arrays.copyOfRange(bytes, 32, 64))));
    } catch (Exception e) {
      throw new IllegalArgumentException("Invalid EIP-712 signature");
    }
  }

  public static boolean eq(Object a, Object b) {
    return a != null && b != null && a.toString().equalsIgnoreCase(b.toString());
  }

  public static void exact(Map<String, Object> m, String... keys) {
    if (!m.keySet().equals(Set.of(keys)))
      throw new IllegalArgumentException("Unexpected protocol fields");
  }
}
