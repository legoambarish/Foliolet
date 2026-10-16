# PS32 final audit — durable execution progress

## Safety and exact source

The complete 807-line supplied master prompt was read. Work is confined to `feature/ps32-final-winning-audit-20261016-1645`, created directly from verified `feature/digilocker-assisted-intake` HEAD `db55c2c6c1209e567713fa9ab08c5441bd55bc86` (tree `75e3b538a1e04b5a71fbbfc0dc644764d4403de8`, parent `6db30e1520211b0dae88c8b47200a9ed1b6089c7`). Main, cf, source branch and original runtime state have not been modified. All service records, chains and keys used by this run are disposable fixtures.

Container DNS initially blocked cloning. Commit-pinned GitHub Actions archive/Git bundle recovery, SHA-256 verification and an isolated local clone established actual source access; real application tests execute in isolated GitHub Actions. This is not an independent replacement laboratory. The prior Library recovery ZIP was preserved unchanged; historical independent lab results are not credited as current repository tests.

## Durable evidence

Read [docs/ps32-final/EVIDENCE.md](docs/ps32-final/EVIDENCE.md) for exact runs, source commits, counts, conditions, negative cases and artifact boundaries. Earlier ledger versions remain in Git history.

- Original baseline: 108 Java, 74 Django, 22 Node verifier tests plus Solidity integration passed, run 38934429615.
- Independent source-association reproduction: six of eight new cases failed against the baseline, run 38935483259. All eight pass after correction.
- Security regression at `25389eb7bb411ed6746235760a2645f1dcbfee97`: 128 Java, 96 Django, 22 Node verifier tests and Solidity script pass, run 38940240171.
- Real full-stack run 38938026869: 51 lifecycle, 23 security, five Chromium, 12 failure/restart, three CSV checks and companion/OCR/QR suites pass.
- Later full-stack run 38941316476 passes the earlier phases and 15 new actual database/EVM/backend interruption checks. Its final session continuity assertion uses an incorrect `/wallet/` route; fix to actual `/` and rerun. Database failure took 30.012 seconds; a configurable five-second Hikari connection wait is now staged/applied and requires before/after verification.
- Latest inspected run 38943212551: 131 Java tests pass, including the external-AI privacy gate. Django discovers 105 tests, with one genuine-signed-PDF positive control failing in the new signature inspector. The feature is not accepted as working yet; async event-loop/explicit incomplete-result handling is committed at `50309fc7bf83fe12f8f80c95fd7a58c96b1504af` and revalidation is in progress.

## Implemented substantive corrections

- Exact OCR physical-cell/frame/label/value corroboration; correct Candidate/date classification; valid source geometry and confidence scale (`dcfd3a5b1f2660d5b1fc4ec2ed698a3d4429bb6c`).
- Numeric-loopback-only wallet transport, no ambient proxies/redirects, bounded reads, private errors (`3bdf6d59b5683904a83b977812fd639f87f720e3`).
- Owner-only POSIX vault/key/ciphertext, no-overwrite keys, strict identifiers, symlink containment and bounded ciphertext reads (`193a287417da68e931909fc0c3359be80f7913fe`).
- Cross-platform fictional fixture fonts, configurable UI/RPC and Linux Chromium execution; actual full-stack assertions preserved.
- AES-GCM encrypted Django JSON database sessions, key-separated context, legacy signed-JSON compatibility, explicit non-destructive `reencrypt_sessions` command, retained session IDs/expiry and owner-only Django key creation.
- Bounded 20-MiB original upload reads and private Spring API browser-Origin rejection.
- Legacy external analysis default-denied before source reads/network unless an administrator explicitly enables it, the request explicitly consents, and a provider key exists. An empty API key is not a privacy boundary. No cloud processing was enabled here.
- Narrow local PDF signature inspection: exact source hash, strict current-file coverage, bounded isolated worker, no implicit trust roots, no `ISSUER_VERIFIED` promotion. Real positive/tampered signed-PDF tests are required before accepting the new feature.

No existing credential, Merkle, presentation-signature or provenance encoding was changed. No stored keys were rotated or originals re-encrypted silently.

## Document evaluation completed

Controlled complete run 38940026280 compares exact baseline and repaired pipeline on identical Linux-generated 14 fictional PDFs / 169 labelled facts. Both: 168 correct unique pairs, 170 suggestions, recall 99.4083%, precision 98.8235%, zero incorrect automatic suggestions, two incorrect review suggestions, 769/769 exact source fragments. This audit preserved accuracy; it did not improve the already-repaired corpus score. Median 4.412 vs 4.346 seconds; sampled process-tree maximum RSS 528,478,208 vs 520,626,176 bytes. Single-pass timings do not prove a speedup or resolve the earlier different-hardware 43.4-second case.

Eight genuine CC-BY-4.0 CORD receipts were acquired with original human labels and image hashes: train rows 0/10 calibration, test 0/7/14/21/28/35 held out, selected before outputs. All completed; seven suggestions, all review-required, zero automatic, 16/16 source fragments exact. Held-out grand totals: 4/6 correct normalized decimals; 5/6 correct source total literals including one unnormalized `RP38.000`; one misassociated identifier. This is not general receipt or Indian academic accuracy. Initial HTTP 500/502 download failures were preserved; retries used the same selected rows. No held-out tuning was done.

## Verified research and product direction

Official PS32 tracks page is open-ended Web3 ownership/identity/trust/value with innovation priority. Other problem statements' Sarvam/Gemini mandates do not apply to PS32. Event metadata: 17 October 2026 09:00 IST through 18 October 15:00 IST; overview says 24 hours. Exact scoring weights and prebuilt-code eligibility are unverified. Do not invent them.

Primary research includes W3C VC 2.0, RFC 9901 SD-JWT, OpenID4VP 1.0, DigiLocker, Blockcerts, walt.id, CCA signature/root guidance, CORD, DocLayNet, pyHanko and Ollama. Position Foliolet as source-reviewed selective disclosure with explicit assurance boundaries, not a novel Merkle tree or universal issuer-verification platform.

## Active/remaining work

Finish signature positive-control diagnosis; correct final resilience route and repeat real E2E after latest changes; collect actual local-model and supply-chain/static-audit evidence from the extended workflow; finish whole-module coverage, dependency reachability and A–L reports; final demo/judge/claims/verdict documents; remove temporary privileged patch workflow; final source snapshot and protected-branch verification.

Existing Spring npm advisories (39: 2 low, 9 moderate, 23 high, 5 critical), largely Ganache bundled dependencies, remain unresolved pending reachability analysis. Legacy document storage is plaintext and outside the encrypted-wallet claim. Windows ACLs, physical NFC, genuine Indian documents and real issuer authority remain unverified.

Before final delivery remove `.github/workflows/ps32-apply-reviewed-patch.yml`. It is a temporary exact-HEAD-leased, branch-only literal-patch transport, not a permanent application workflow. Retain reviewed patch provenance but never keys, bearer tokens, source-private documents or unredacted diagnostics. Preserve negative results and distinguish pending work from executed passes.
