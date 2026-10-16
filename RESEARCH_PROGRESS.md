# PS32 final audit — durable progress

## Safety and baseline

The full 807-line master prompt was read. Work is confined to `feature/ps32-final-winning-audit-20261016-1645`, created at verified remote source `db55c2c6c1209e567713fa9ab08c5441bd55bc86`, tree `75e3b538a1e04b5a71fbbfc0dc644764d4403de8`, parent `6db30e1520211b0dae88c8b47200a9ed1b6089c7`. No edits or merges to main, cf or the source branch; no original runtime, documents, accounts, keys, EVM state or models touched.

Container GitHub DNS failed. Real source access and execution were recovered through GitHub Actions plus a SHA-256-checked archive/Git bundle cloned into an isolated local directory. Full local snapshot `0627643118c28fc3bdedc4b2d8705d4d48739ea7`; real builds and full-stack services run in disposable Ubuntu CI. Previous Library research archive recovered intact; its independent lab findings are not relabelled as repository test results.

## Executed evidence

### Original application baseline — PASS

https://github.com/legoambarish/Foliolet/actions/runs/38934429615 at `d610a5e3d2e240c5f36d406503b9866ad4711b86`:
108 Java, 74 Django, 22 Node verifier tests; all pass. Solidity integration script passes authorization, immutable roots, unsupported assurance rejection, supersession, revocation and seven Merkle shapes. No invented Solidity assertion count. `pip check` passes. Ubuntu 24.04.5, Java 21.0.12, Python 3.13.16, Node 22.23.3, Tesseract 5.3.4. Artifact 12060885684 downloaded.

### Independent adversarial reproduction — RED

https://github.com/legoambarish/Foliolet/actions/runs/38935483259 at `f5b0ed977b9e0fdc09cb08541086c7249cd911ee`:
SourceAssociationRegressionTest has 8 tests: six fail against baseline, two valid controls pass. Failures are Candidate/date collision; different-cell OCR false corroboration; different-rotation false corroboration; conflicting-label corroboration; off-page geometry; confidence outside 0–100. Artifact 12060817348 downloaded; actual XML inspected.

### Source and vault fixes — GREEN Java; Django helper error found and corrected

https://github.com/legoambarish/Foliolet/actions/runs/38938027342 at `2d5ca083370ba1ffe1c60b7dc468d16611aa2b4b`:
124 Java tests PASS, including all eight SourceAssociationRegressionTest and eight PrivateVaultSecurityTest cases. Django discovered 83 tests but six new transport cases errored because the test helper `client()` collided with Django's own `self.client` object. This was an audit test defect, not a production regression; corrected at `a7637e22d41f30d244d3d7d2d59ecb8e15066cbf` and an additional two-loopback-server HTTP 307 body-forwarding test was added. Do not call the full regression run green until rerun evidence is retrieved. Artifact 12061503277 inspected.

### Actual full-stack application — PASS

https://github.com/legoambarish/Foliolet/actions/runs/38938026869 at `2d5ca083370ba1ffe1c60b7dc468d16611aa2b4b`:
- 51 real HTTP/PostgreSQL/Ganache/Web3j/Django lifecycle checks PASS: authentication, source review, anchoring, independent Node validation, nine proof tamper cases, one-time concurrent release, expiry, revocation, supersession, encrypted-original/backup tampering, restartable watcher and session-bound proof export.
- 23 real security checks PASS: username race/DB uniqueness, Django login and confirmation, absence of extracted suggestion copies from sessions, canonical proof rejection, trust pins, hidden-fact exclusion and threshold-label protections.
- 5 real Chromium browser checks PASS: 19 exact native-table facts; upload/review/anchor/selective share/independent browser verification; 19 scanned review cards with zero automatically accepted facts; server-side edit tracking from 91 to 95; no JS errors or document requests beyond loopback.
- 12 failure/restart checks PASS: real missing local model and OCR; exact original preservation; interrupted-job marking and retry; oversized upload. Model metadata/injection/delay cases use a local HTTP test double, explicitly not real oversized weights or actual Ollama inference.
- 3 CSV fallback checks PASS. Watcher, OCR-worker and QR suites also executed successfully; exact counts pending final extraction.
- Disposable PostgreSQL 17, fresh private EVM, Java heap 768 MiB, independent deployment pins, bundled Chromium, Tesseract plus complementary offline OCR. Actual physical NFC, Windows/macOS and public internet tunnel not tested here.
Artifact 12061479169 downloaded with result JSON and three fictional browser screenshots. Artifacts expire after 14 days; durable summaries/reports must be committed.

## Meaningful production/test commits

- `dcfd3a5b1f2660d5b1fc4ec2ed698a3d4429bb6c`: exact physical-cell/rotation/label/value corroboration, valid geometry/confidence, correct date-label classification.
- `3bdf6d59b5683904a83b977812fd639f87f720e3`: numeric-loopback-only wallet bridge, no ambient proxies/redirects, bounded streamed responses, controlled errors.
- `193a287417da68e931909fc0c3359be80f7913fe`: owner-only POSIX vault/key/ciphertext permissions, no-overwrite key retention, symlink/path rejection, bounded ciphertext reads, unchanged AES-GCM and commitment formats.
- `53cc24ed8f4930ca3b4dd0c6196056cf19289595` and `4a3d0ad34374bf929de91282b633450c1117a11f`: explicit cross-platform fixture fonts, Linux Chromium, configurable test UI/RPC; no acceptance assertions weakened.
- `cb641a54db1197364a312840bc5bb833c8a670be`: bounded cross-platform actual-pipeline evaluator with source hashes, unique-field recall and real RSS sampling; no implicit private inventory.
- `5e7b1dd00f86ab725fbdd41465fa4c4291d8cb9a`: licensed public CORD corpus acquisition with frozen two-row calibration and six-row held-out split; no academic accuracy inferred.
- `058cd0e7fb4035f0651e5dec9ebffe7295c1e652`: controlled exact-source before/after and held-out evaluation workflow. Results pending.

## Verified challenge and research

Official PS32 wording now independently retrieved from the organizer's tracks page: https://www.commudle.com/communities/cdn-commudle-developer-network/hackathons/hack-sprint/tracks . It is open-ended Web3 ownership/identity/trust/value with explicit innovation priority. Sarvam/Gemini mandates belong to other problem statements, not PS32. Dates show 17 October 2026 09:00 IST to 18 October 2026 15:00 IST; overview markets 24 hours, so do not infer exact submission cutoffs. Numerical judging rubric and prebuilt-code eligibility are not verified.

Primary sources researched: W3C VC Data Model 2.0, RFC 9901 SD-JWT, final OpenID4VP 1.0, Blockcerts, walt.id, India's CCA signature-verification/root-certificate guidance, CORD and DocLayNet, local Ollama Qwen3:4b, pyHanko. Plain commitments do not establish issuer truth; CCA requires signer/issuer chain and relevant revocation evidence. No government API partnership, hosted private-document upload or paid model service is enabled.

## Unresolved / next work

Complete controlled document benchmark and held-out label review; whole-module audit/coverage and dependency reachability; Django key/session-at-rest and upload bounds; issuer-assurance policy and feasible local validation; further outage/restart checks; final A–L reports, architecture, claims, judge defense, cross-platform guide and readiness verdict.

Spring npm baseline has 39 advisories (2 low, 9 moderate, 23 high, 5 critical), largely Ganache/bundled transitive dependencies. No blind forced downgrade. Legacy document path may store plaintext and must be separated from wallet confidentiality claims. POSIX hardening is not Windows ACL certification or protection from a compromised same-user/root host.

Before final delivery remove `.github/workflows/ps32-apply-reviewed-patch.yml`, the temporary exact-HEAD-leased, branch-only reviewed-patch transport. No private or secret material belongs in final artifacts. Preserve negative results, distinguish historical metrics from this run, and never equate green unit tests with universal real-document accuracy or issuer verification.
