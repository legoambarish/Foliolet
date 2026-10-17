# Final architecture and product roadmap

## 1. Recommended architecture

Retain the tested architecture for the finale. Do not replace working proof or storage protocols. This is a custodial platform with independently checkable commitments, not a fully decentralized identity system.

```text
Holder / local intake folder
       |
       v
Private Django UI -- authenticated, CSRF-protected, encrypted DB sessions
       |
       | numeric loopback; explicit Basic credentials; no proxies/redirects
       v
Spring Boot wallet / policy / ownership / version authority
       |                       |                       |
       v                       v                       v
Encrypted original vault   PostgreSQL            Bounded reader jobs
AES-GCM + preserved key    claims/grants/state    PDFBox / OCR / local Foli
       |                       ^                       |
       |                       | source-bound suggestions, never authority
       +-----------------------+<-- explicit holder review/confirmation
                               |
                     canonical typed claims + salts
                               |
                     Merkle root + document commitment
                               |
                     operator-authorized EVM registry
                               |
                     selected leaves + signed policy
                               |
Recipient / separate receiver / downloaded proof bundle
                               |
             independent JS or Node verifier + separately pinned network
                               |
               mathematical validity AND online lifecycle status
```

Parallel private feature: Django retrieves the exact authorized original and invokes the bounded PDF-signature worker. It reports digest validity, signature mathematics and current-file coverage. It has **no implicit issuer roots**, cannot elevate assurance, and is not part of the existing portable proof format. The user's original is not sent to a certificate website or hosted model.

## 2. Authority model

The original byte hash identifies which source was processed. A source fragment identifies which text supported a proposed field. Review records whether the holder accepted or modified it. A Merkle inclusion proof establishes that the selected canonical claim belongs to the committed root. A custodial signature binds the platform's presentation and policy. A chain query establishes the relevant recorded status at verification time.

None of those alone establishes an issuer's truthfulness or authority. The signature inspector can establish mathematical properties of supported signatures while leaving issuer trust unknown. `issuerVerified=false` is intentional, not a missing CSS color. A future issuer policy must independently define trusted issuers, authorized credential types, trust anchors, certificate/revocation/time handling and error behavior before assurance can be upgraded.

Keep these assurance dimensions separate in UI and reports: source support, holder review/modification, commitment integrity, presentation signature, online freshness and issuer authority. Do not collapse them into a single green badge.

## 3. Why not rewrite now?

The existing stack already has verified behavior across Java, Django, Node, Solidity, real PostgreSQL/EVM services and Chromium. Replacing Django or Spring would add migration and authentication risk without improving the central privacy demonstration. Introducing a new canonicalization or credential format could invalidate old proofs. Reinitializing Ganache or keys would destroy the very continuity the restart tests establish.

For later production, use supported chain infrastructure or an independently audited transparency service, hardened app deployment, OS-level document isolation and standardized credential protocols where appropriate. These are explicit migrations. The current local chain is a demonstration deployment with operator trust pins; it is not an acceptable production claim merely because its API resembles a public chain.

## 4. Prioritization method

The assignment's factors are treated as an engineering decision aid, not measured probabilities of winning. Scores are ordinal 1–5. Priority index = judge impact × practical usefulness × technical credibility × feasibility ÷ regression risk. Risk 1 is lowest and 5 highest, so the ranking does not accidentally reward dangerous changes. Effort is relative rather than a promised implementation time.

| Improvement | Impact / usefulness / credibility / feasibility / risk | Index | Effort | Decision |
|---|---|---:|---|---|
| Preserve independent proof rejection and one-time lifecycle evidence | 5 / 5 / 5 / 5 / 1 | 625 | Small | Existing capability retained and revalidated, not rebuilt |
| Repair false OCR corroboration and source-review trust boundaries | 5 / 5 / 5 / 5 / 1 | 625 | Medium | Implemented with baseline red/green tests |
| Controlled synthetic + held-out real-document evidence | 5 / 5 / 5 / 4 / 1 | 500 | Medium | Executed; negative outcomes retained |
| Prevent silent private-document cloud egress | 5 / 5 / 5 / 4 / 1 | 500 | Small | Default-deny gate implemented and tested |
| Encrypt private sessions and preserve keys | 4 / 5 / 5 / 4 / 2 | 200 | Medium | Implemented with migration/restart evidence |
| Local signature mathematics with honest issuer uncertainty | 5 / 4 / 4 / 4 / 2 | 160 | Medium | Implemented narrowly; real signed/tampered controls |
| Dependency hardening and reproducible full-stack CI | 4 / 5 / 5 / 4 / 2 | 200 | Medium | Implemented; remaining advisory results explicit |
| Full holder-key / VC / OpenID presentation redesign | 5 / 5 / 5 / 2 / 5 | 50 | Large | Defer until after the tested finale core |
| New zero-knowledge eligibility circuit | 5 / 3 / 3 / 1 / 5 | 9 | Large | Reject for this finale; no unsupported ZK claim |
| Decorative NFT or unrelated agent features | 2 / 1 / 2 / 3 / 3 | 4 | Medium | Reject: weak user value and distracts from evidence |

## 5. P0 — core truth and privacy

Completed: source corroboration repairs; private-cloud egress gate; strict source/evidence handling; retained tamper rejection; explicit unsupported issuer state. Required presentation rule: never equate Merkle validity, a QR or a self-signature with institutional issuance. The audit did not knowingly leave one of its reproduced P0 demo-path defects unfixed, but it cannot certify absence of undiscovered defects.

Release acceptance: genuine positive proof still passes; mutated proof fails; arbitrary model output cannot anchor a fact; wrong-source signature output fails binding; absent chain/database cannot be labelled verified. These tests are retained in the repository.

## 6. P1 — reliability, useful trust and deployment safety

Completed or explicitly validated in the final register: owner-only vault/key handling; encrypted sessions and compatible migration; no-redirect/no-proxy wallet transport; original upload bounds; browser-Origin boundary; dependency patches; exact branch-aware Windows launcher; bounded heap; actual database/EVM/backend restart; real signature-inspection UI and source hashes.

Remaining before production: a supported chain runtime and remaining bundled dependency remediation; ingress-wide authentication/rate limits; a formal issuer authority policy with real signed credential corpus; OS-level sandboxing and service resource quotas; production web server/TLS/secret management; removal or isolation of plaintext legacy endpoints. These are not hidden behind a successful local demo.

## 7. P2 — stronger architecture and measured scale

Introduce an explicit transactional outbox/reconciliation process for SQL/EVM/file-state transitions. Add fault injection at every transition and backup restore drills. Separate signing/encryption keys, document a rotation/re-encryption protocol, and protect secrets with platform facilities. Introduce recipient-authenticated grants and holder-controlled consent signatures where the threat model needs them.

Develop typed issuer/schema adapters and larger genuine, consented academic datasets. Split development, calibration and held-out sets before tuning; report per-layout uncertainty, false automatic acceptance and unsupported formats. Test sustained concurrent OCR and model workloads on the actual presentation hardware, not only isolated reader processes.

Standards adapters should target specific W3C VC / SD-JWT / OpenID4VP profiles with conformance tests. Do not rename existing JSON to “VC compliant.” Consider a separate evidence-resolution API that lets a verifier understand source review without disclosing unrelated fields or original bytes.

## 8. P3 — optional polish

Accessibility review, keyboard paths, clearer error copy, responsive receiver refinements and carefully labelled prerecorded fallback footage are useful after acceptance gates pass. NFC can launch the same disclosure URL, but must not be described as preventing copying or authenticating the recipient. Physical NFC remains a hardware test, not a software claim established by QR rendering.

## 9. Non-goals and migration constraints

No new blockchain token; no cloud upload by default; no issuer badge from logo/QR; no silent reset of private data; no incompatible claim canonicalization; no assertion of ZK eligibility; no automatic replacement of functioning OCR by a model because it emits more fields. Existing proofs remain interpretable under the original protocol. Session encryption has explicit compatibility and migration rather than a key reset.

The final product is strongest when one recipient can verify exactly the chosen fact, see how it was sourced, understand what is not known, and observe an attack being rejected. That is the architecture to defend.
