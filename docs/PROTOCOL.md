# Salted Merkle presentation format v1

These encodings are protocol behavior. Change the format/version when changing canonicalization or encoding; do not silently rebuild an existing credential. Java and the independent browser/Node implementation agree on live proof bundles.

Let `field(s)` be uint32 big-endian UTF-8 byte length followed by the UTF-8 bytes. `enc(s1,...,sn)` concatenates fields. Hex strings are lowercase `0x` encodings; raw hashes and salts are 32 bytes. Times in hash encodings are decimal Unix seconds. JSON is transport only, not the hashing representation.

## Facts

Paths use lowercase dot-separated identifiers; labels and text use Unicode NFC, surrounding whitespace removal and no control characters. Values are typed (`string`, `decimal`, strict ISO `date`, `boolean`). Decimals have fixed notation, no exponent and no trailing zeros; negative zero is zero. Dates are valid `yyyy-MM-dd`; booleans are `true`/`false`. Confirmed facts are sorted by canonical path. Every leaf has an independent cryptographically random 32-byte salt and zero-based index.

```
format = "salted-merkle-keccak-v1"
leaf = keccak256(0x00 || enc(format, path, label, type, value, derivedFrom)
                 || salt32 || index_uint32_be)
parent = keccak256(0x01 || left32 || right32)
```

Duplicate the last node of an odd level. The proof lists sibling hash and LEFT/RIGHT direction at every level. Verifiers check index, leaf count (1..128), expected depth, side at each index and duplicate-odd-node consistency, then compare with the root. Only selected leaves, their salts and siblings are disclosed. Labels/type/derivation metadata are bound to each leaf. Normal confirmation accepts at most 64 input facts; the automatically added threshold may make 65 leaves.

```
documentCommitment = keccak256(0x02 || documentSalt32 || keccak256(originalBytes))
```

The original bytes, raw document hash and salt do not go on-chain or into presentations. Commitment membership associates holder-confirmed claims with an anchored document state; it is not a computation proving those claims were faithfully extracted from the document.

## Provenance and signed presentation

```
provenanceDigest = keccak256(enc("provenance-v1", level, explanation,
    firstServerReceiptEpochOrEmpty, lastServerReceiptEpochOrEmpty,
    observationCount, observedChanges, enrollmentMatchesFirst, agentIdOrEmpty))
```

The envelope hash is Keccak of byte `0x03`, followed by length-prefixed strings in this exact order:

```
format, credentialId, credentialVersion, merkleRoot, leafCount,
lowercaseContract, chainId, lowercaseOperator, documentCommitment,
provenanceDigest, provenanceCode, anchoredAtEpoch,
grantId, verifierLabel, purpose, nonce, createdAtEpoch, expiresAtEpoch, oneTime
```

Append each disclosed leaf's raw hash in bundle order. The platform signs the resulting 32-byte envelope hash with EIP-191 personal-message prefix. `platformSignature` is r32 || s32 || v1. `envelopeHash` and recomputed provenance digest must match; recovered signer must equal the independently pinned platform operator and contract's immutable operator. `anchor.txHash` is informational, excluded because recovered anchors may lack the original receipt; trust the contract record rather than this display metadata.

Verify configured chain/registry/operator, commitment fields, provenance code, version and anchor timestamp against the current contract record. Status must be ACTIVE. Expiry and created-time bounds are checked; the presentation cannot exceed seven days. Link revocation and one-time release counters are additional service policy. Cryptographic verification of a retained bundle cannot prove that the bearer is the intended recipient or erase copied facts.

## First-seen agent messages

```
message = enc("first-seen-v1", agentId, itemUuid, filename, sha256Hex,
              localObservedEpoch, sequence, previousDigest)
signature = HMAC-SHA256(agentSecret32, message)
digest = keccak256(message)
```

The service validates active agent ownership, signature, contiguous sequence and previous digest. Identical replay returns the existing acknowledgement; conflicting replay fails. New observations must arrive within 24 hours and cannot claim a time more than 60 seconds ahead. The server records its own received clock. An outbox older than 24 hours requires operator recovery/new pairing; it is not silently accepted as historical continuity.
