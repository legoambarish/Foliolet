package com.sih26190.dms.selective;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Component;
import org.web3j.crypto.Hash;
import org.web3j.utils.Numeric;

@Component
public class MerkleTreeService {
  public static final String FORMAT = "salted-merkle-keccak-v1";
  private final SecureRandom random = new SecureRandom();

  public record Leaf(
      String path,
      String label,
      String type,
      String value,
      String derivedFrom,
      String salt,
      int index) {}

  public record Step(String sibling, String side) {}

  public record RevealedClaim(Leaf leaf, List<Step> proof) {}

  public String randomHex() {
    byte[] bytes = new byte[32];
    random.nextBytes(bytes);
    return Numeric.toHexString(bytes);
  }

  // UTF-8 strings have unsigned 32-bit big-endian byte lengths. Index is uint32.
  public static byte[] encode(String... fields) {
    try {
      var bytes = new ByteArrayOutputStream();
      var out = new DataOutputStream(bytes);
      for (String field : fields) {
        byte[] utf8 = field.getBytes(StandardCharsets.UTF_8);
        out.writeInt(utf8.length);
        out.write(utf8);
      }
      return bytes.toByteArray();
    } catch (java.io.IOException impossible) {
      throw new IllegalStateException(impossible);
    }
  }

  public static byte[] hex32(String value) {
    if (value == null || !value.matches("0x[0-9a-fA-F]{64}"))
      throw new IllegalArgumentException("Expected 32-byte hex");
    return Numeric.hexStringToByteArray(value);
  }

  public String leafHash(Leaf leaf) {
    if (leaf.index() < 0) throw new IllegalArgumentException("Invalid leaf index");
    try {
      var bytes = new ByteArrayOutputStream();
      var out = new DataOutputStream(bytes);
      out.writeByte(0);
      out.write(
          encode(FORMAT, leaf.path(), leaf.label(), leaf.type(), leaf.value(), leaf.derivedFrom()));
      out.write(hex32(leaf.salt()));
      out.writeInt(leaf.index());
      return Numeric.toHexString(Hash.sha3(bytes.toByteArray()));
    } catch (java.io.IOException impossible) {
      throw new IllegalStateException(impossible);
    }
  }

  public String parent(String left, String right) {
    byte[] data = new byte[65];
    data[0] = 1;
    System.arraycopy(hex32(left), 0, data, 1, 32);
    System.arraycopy(hex32(right), 0, data, 33, 32);
    return Numeric.toHexString(Hash.sha3(data));
  }

  public List<List<String>> tree(List<Leaf> leaves) {
    if (leaves.isEmpty() || leaves.size() > 128)
      throw new IllegalArgumentException("Commit between 1 and 128 facts");
    for (int i = 0; i < leaves.size(); i++)
      if (leaves.get(i).index() != i)
        throw new IllegalArgumentException("Indices must be consecutive");
    var levels = new ArrayList<List<String>>();
    levels.add(leaves.stream().map(this::leafHash).toList());
    while (levels.get(levels.size() - 1).size() > 1) {
      var previous = levels.get(levels.size() - 1);
      var next = new ArrayList<String>();
      for (int i = 0; i < previous.size(); i += 2)
        next.add(parent(previous.get(i), previous.get(Math.min(i + 1, previous.size() - 1))));
      levels.add(next);
    }
    return levels;
  }

  public String root(List<Leaf> leaves) {
    var levels = tree(leaves);
    return levels.get(levels.size() - 1).get(0);
  }

  public List<Step> proof(List<Leaf> leaves, int index) {
    if (index < 0 || index >= leaves.size()) throw new IllegalArgumentException("Unknown fact");
    var levels = tree(leaves);
    var result = new ArrayList<Step>();
    for (int level = 0; level < levels.size() - 1; level++) {
      var row = levels.get(level);
      int sibling = index ^ 1;
      result.add(
          new Step(row.get(Math.min(sibling, row.size() - 1)), index % 2 == 0 ? "RIGHT" : "LEFT"));
      index /= 2;
    }
    return result;
  }

  public boolean verify(Leaf leaf, List<Step> proof, int count, String root) {
    try {
      hex32(root);
      if (count < 1 || count > 128 || leaf.index() < 0 || leaf.index() >= count || proof == null)
        return false;
      String hash = leafHash(leaf);
      int index = leaf.index(), width = count, level = 0;
      while (width > 1) {
        if (level >= proof.size()) return false;
        Step step = proof.get(level++);
        boolean right = index % 2 == 0;
        if (!step.side().equals(right ? "RIGHT" : "LEFT")) return false;
        if (right && index + 1 >= width && !hash.equalsIgnoreCase(step.sibling())) return false;
        hash = right ? parent(hash, step.sibling()) : parent(step.sibling(), hash);
        index /= 2;
        width = (width + 1) / 2;
      }
      return level == proof.size() && hash.equalsIgnoreCase(root);
    } catch (RuntimeException e) {
      return false;
    }
  }
}
