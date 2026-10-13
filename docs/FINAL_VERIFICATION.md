# Final verification, 13 October 2026

Branch: testbuilds. Original HEAD: `435f5e6466468fac40304c8081b358a83b727450`. Main remains `c04741ee68563566dc82ab4e71b97c3898714f72`. All implementation and commits are local; no remote push, merge, publication or tunnel exposure occurred. Preexisting untracked evolution report/output and original wallet state are preserved.

<!-- MACHINE_RESULTS -->
| Executed check | Actual result |
| --- | --- |
| Maven | 26 tests, 0 failures, 0 errors |
| Node verifier, canonical vectors and governed real-EVM suite | 23/23 pass |
| Django including restricted public routing | 24 tests, passed=True |
| Primary live workflow | 24 checks, passed=True |
| Approval/import/secondary live workflow | 62 checks, passed=True |
| Issuance persistence-gap simulation | 3 checks, passed=True |
| Browser rehearsal | 18 assertions, 0 page errors |
| Spring grounded boundary | GROUNDED_ASSISTANCE, modelUsed=True, 2.828 seconds |
| App/AI stopped, direct RPC reader | Historical PASS; current PASS |
| RPC stopped | Current UNKNOWN |
| Fresh contract ABI/bytecode compile | Matching hashes: True |
| Narrow source secret scan | 284 files; 0 suspected matches |
| Npm development dependency audit | 38 findings, including 5 critical and 24 high |

Packaged jar SHA-256: `b501d2102a4857bfca60b1362335f4476a145093cab72c12a831d9db94a5ec12`. Test evidence hashes and detailed counters are in [verification-results.json](verification-results.json).
<!-- END_MACHINE_RESULTS -->

## Executed commands and scope

`spring-boot-service/mvnw.cmd -f spring-boot-service/pom.xml package -q` tested and packaged the implementation. Counts come from Surefire XML. `node --test ...test-proof-security.cjs ...test-verifier-ui.cjs ...test-bridge-contracts.cjs` passed; the latter is a comprehensive real-EVM test with many assertions, counted as one Node test. The separate `node spring-boot-service/scripts/test-contracts.cjs` legacy EVM script also passed authority, immutable roots, assurance guards, supersession/revocation and seven Merkle shapes; do not add its assertions to unit-test counts.

`.venv/Scripts/python.exe django-service/manage.py test dashboard` passed. `docker compose config --quiet` passed. Native fresh-state reset archived only isolated demo directories and launched services successfully; managed stop/restart retained the same chain code/governance pins. `rehearse-bridge.ps1 -ProveOffline` created fixtures with AI stopped, stopped private Spring/Django, ran direct reader historical/current verification, stopped RPC for UNKNOWN, then restored services. The public-only preview was still loopback and did not supply proof authority.

`tools/test-issuance-recovery.py --simulate-persistence-gap` tests exact-input issuance idempotency and reconciles a pending database lifecycle against an existing immutable chain record. It explicitly simulates the gap; no actual process crash was injected. `node tools/test-demo-ui.cjs` exercised real role pages, browser holder keys/encrypted backup, issuance, request, inline approval, verifier receipt, independent reader, mock overlay and a 390-pixel viewport. It also executed the rogue-refusal control, revoked the browser credential, reproduced historical PASS beside current FAIL, and confirmed the approval card has no clipped signing controls. Test-harness option-loading races were fixed before the passing run. Screenshots were inspected locally, and captures remain ignored.

`tools/test-local-assistant.py` uses a hostile fake document, validates source quotes and proves chat does not change credentials/grants. Early model-written quotations were rejected. The implementation now resolves only validated numbered source spans into exact server-owned quotations; unknown or widened references are rejected. Model interpretation is still unverified and never enters receipts. Direct local text/vision benchmark negative outcomes are retained in [LOCAL_AI_BENCHMARK.md](LOCAL_AI_BENCHMARK.md).

`node .../compile-contracts.cjs` produced identical ABI and bytecode hashes before/after a fresh compile. `tools/scan-source-secrets.py` scans tracked and implementation source for a narrow set of API-token/private-key patterns, excluding ignored vaults and preserved user artifacts. Zero matches is not an exhaustive secret certification. `pip check` reports no broken requirements; it is not a CVE audit. Npm audit remains nonzero because archived Ganache bundles vulnerable development libraries. Ethers was updated to 6.17.0 and tmp overridden to 0.2.6 without changing the Solidity compiler. Use this chain only on loopback with public test identities.

## Unavailable and simulated

- Docker image build, Compose health/start/reset and GitHub Actions execution: UNVERIFIED. The installed engine failed on an inaccessible stale socket. Automatic approval review rejected removal by policy; no alternative deletion bypass was attempted.
- Real issuer authority, production governance/key custody and real-world factual truth: not established. Both native templates use simulated recognized issuers.
- Setu live sandbox session and authentic DigiLocker XML: NOT TESTED. No authorized credentials or real issuer sample was available. Supported XML validation is a narrow explicit test profile with independent certificate/scope pins. Crypto tests use real RSA signatures and a fixture certificate object, not institutional onboarding.
- External public tunnel, phone tap and secure NFC challenge: NOT TESTED. No external exposure or hardware execution occurred. Static tags remain clonable pointers.
- Optional vision UI, URL-fragment encryption, automated GHCR publisher and recorded backup video: CUT. A labeled recording script exists. Public TLS intermediaries can observe disclosed facts.

## Remaining priorities

P0: execute the committed Compose stack on a functioning Docker engine, then run its smoke test. Until then Phase 0 retains a runtime acceptance gap.

P1: replace/harden archived Ganache dependencies before non-demo use; onboard actual issuer authority and supported source schemas; use production institutional signer custody and stronger browser-key recovery; enforce production service authentication/TLS/rate controls; test true cross-resource process crashes and a reconciler; implement/test provider-side cancellation/revocation. Native scripts currently trust a matching loopback service when a port is occupied, so use a clean isolated operator environment.

P2: physical NFC rehearsal, tested tunnel hostname/callback lifecycle, optional fragment encryption, broader supported XML and document formats, image UI after representative benchmarks, and a labeled backup video recording. None of these gaps is silently counted as verified.
