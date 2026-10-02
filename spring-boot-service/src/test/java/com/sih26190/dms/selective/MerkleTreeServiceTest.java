package com.sih26190.dms.selective;

import static org.junit.jupiter.api.Assertions.*;

import com.sih26190.dms.selective.MerkleTreeService.*;
import java.util.*;
import org.junit.jupiter.api.Test;

class MerkleTreeServiceTest {
  final MerkleTreeService merkle = new MerkleTreeService();
  final ClaimCanonicalizer canonical = new ClaimCanonicalizer();

  Leaf leaf(int i) {
    return new Leaf(
        "fact.f" + i, "Fact " + i, "string", "Private " + i, "", "0x" + "12".repeat(32), i);
  }

  @Test
  void allTreeShapesAndMultipleDisclosures() {
    for (int count : new int[] {1, 2, 3, 4, 5, 8, 17, 128}) {
      List<Leaf> leaves = new ArrayList<>();
      for (int i = 0; i < count; i++) leaves.add(leaf(i));
      String root = merkle.root(leaves);
      assertEquals(root, merkle.root(leaves));
      for (int i = 0; i < count; i++)
        assertTrue(merkle.verify(leaves.get(i), merkle.proof(leaves, i), count, root));
    }
  }

  @Test
  void everyDisclosedComponentIsBound() {
    var leaves = List.of(leaf(0), leaf(1), leaf(2));
    var proof = merkle.proof(leaves, 0);
    String root = merkle.root(leaves);
    Leaf l = leaf(0);
    for (Leaf changed :
        List.of(
            new Leaf(l.path(), l.label(), l.type(), "Wrong", l.derivedFrom(), l.salt(), 0),
            new Leaf(
                l.path(), "Misleading label", l.type(), l.value(), l.derivedFrom(), l.salt(), 0),
            new Leaf(l.path(), l.label(), l.type(), l.value(), "forged.source", l.salt(), 0),
            new Leaf(
                l.path(), l.label(), l.type(), l.value(), l.derivedFrom(), merkle.randomHex(), 0),
            new Leaf(l.path(), l.label(), l.type(), l.value(), l.derivedFrom(), l.salt(), 1)))
      assertFalse(merkle.verify(changed, proof, 3, root));
    var altered = new ArrayList<>(proof);
    altered.set(0, new Step(merkle.randomHex(), "RIGHT"));
    assertFalse(merkle.verify(l, altered, 3, root));
    altered.set(0, new Step(proof.get(0).sibling(), "LEFT"));
    assertFalse(merkle.verify(l, altered, 3, root));
    assertFalse(merkle.verify(l, proof, 3, merkle.randomHex()));
    assertFalse(merkle.verify(l, List.of(), 3, root));
    assertNotEquals(
        root,
        merkle.root(
            List.of(
                new Leaf(
                    l.path(),
                    l.label(),
                    l.type(),
                    l.value(),
                    l.derivedFrom(),
                    merkle.randomHex(),
                    0),
                leaf(1),
                leaf(2))));
  }

  @Test
  void sharedCanonicalVectorsAgreeWithIndependentVerifier() throws Exception {
    var rows = new com.fasterxml.jackson.databind.ObjectMapper().readTree(
        getClass().getResourceAsStream("/canonical-vectors.json"));
    for (var row : rows) {
      boolean accepted;
      try {
        accepted = canonical.value(row.get("type").asText(), row.get("value").asText())
            .equals(row.get("value").asText());
      } catch (RuntimeException e) { accepted = false; }
      assertEquals(row.get("valid").asBoolean(), accepted, row.toString());
    }
  }

  @Test
  void canonicalTypesAndUnicode() {
    assertEquals("8.5", canonical.value("decimal", "08.500"));
    assertEquals("0", canonical.value("decimal", "-0.00"));
    assertEquals("2026-10-02", canonical.value("date", "2026-10-02"));
    assertEquals("true", canonical.value("boolean", " TRUE "));
    assertEquals("é", canonical.value("string", " e\u0301 "));
    for (String bad : List.of("1e9", "NaN", "8.5\u001f"))
      assertThrows(RuntimeException.class, () -> canonical.value("decimal", bad));
    assertThrows(RuntimeException.class, () -> canonical.value("date", "2026-02-30"));
    assertThrows(RuntimeException.class, () -> canonical.path("Education.CGPA"));
  }
}
