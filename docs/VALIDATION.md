# Audit remediation validation — 2 October 2026

These are local measurements of Foliolet's custodial commitment-verification implementation, not production certification. The complete adversarial report was reviewed before remediation. The existing implementation was preserved. The audit fix introduced no new protocol or ZK feature. Subsequent public packaging applies the Foliolet identity and publishes the repository; it does not deploy a public service.

## Reproduction and remediation

**Publication packaging rerun:** After applying the Foliolet identity and moving fixed development signing keys into ignored local storage, all suites passed again on 2 October 2026: 14 backend tests, 19 Django tests, 22 browser/Node regressions, contract state checks plus 7 tree shapes, 51 live integration checks and 23 live security checks. Django system checks passed and the restarted UI displayed Foliolet. The persisted EVM identity and registry addresses were retained; test signers are now generated in memory.

Publication review covered the candidate source tree and 250 distinct historical blobs across 30 inherited commits. No provider-token or private-key-block findings remained; runtime keys, local databases, vault files, credentials, environment overrides and local validation screenshots are excluded. This is a bounded publication scan, not proof that arbitrary secrets can never occur in source.

| Audit finding | Reproduction before its fix | Result |
|---|---|---|
| HIGH: extracted suggestions in signed sessions | Enrollment left private extracted values in decoded Django session data | Removed the session write. Draft review regenerates suggestions from the encrypted original; confirmation stops returning them. Migration purges retained copies, including expired rows; middleware purges legacy copies on access. |
| HIGH: false/malformed service responses rendered success | False, missing or truthy non-boolean verification flags rendered/cached acceptance | Require literal success for every check and a valid bundle before rendering/caching. Export repeats validation and evicts rejected entries. Service and independent results are distinct. |
| HIGH: missing/circular independent trust pins | Independent checks accepted missing pins; browser defaults came from Spring, and Node did not require all identities | Browser defaults come only from separately provisioned Django-side configuration. Node requires explicit registry/operator/chain pins. Missing, malformed, zero or mismatched identities fail closed. |
| MEDIUM: custom label impersonated a derived threshold | A custom boolean labeled “CGPA at least 8.5” appeared like the recognized derived claim | Holder-authored badge and custom-label prefix; exact recognized path/type/label/derivation tuple required for derived presentation. Canonical metadata remain visible. |
| MEDIUM: username race | A rolled-back direct PostgreSQL probe accepted two identical usernames | Named database uniqueness constraint; concurrent registration returns one success and one controlled HTTP 409. Direct duplicate inserts now fail. |
| MEDIUM: JavaScript/Java validation differences | Signed noncanonical/type-invalid vectors passed JavaScript; Java accepted extra unsigned properties and coerced a boolean claim value into a string | Shared canonical vectors, strict JS schema/types/bounds/canonical values, strict Java public JSON parsing with explicit textual coercion rejection. Existing hash encoding is unchanged. |

Candidate review found two remaining acceptance gaps: Django allowed noncanonical values/paths/derivations and malformed grant IDs, and Java accepted a freshly signed provenance label inconsistent with its numeric anchor code. Both were reproduced with failing regression tests, then fixed. Django validates canonical values and assurance consistency before display/export; Java rejects inconsistent assurance even with a valid platform signature and matching chain digest in the test fixture.

The malicious-custodian disclosure scenario is an architectural boundary, not remediated holder consent: the platform owns plaintext access and signing authority. UI and documentation explicitly state that independent verification cannot establish holder authorization against a malicious platform.

## Final automated validation

The final backend and Django processes were restarted with the patch before live reruns, retaining PostgreSQL, the encrypted vault/key and deployed registry addresses.

| Command / check | Final result |
|---|---|
| Spring: `mvnw.cmd -B package` | PASS: 14 tests, zero failures/errors/skips; executable jar built |
| Django: `..\.venv\Scripts\python.exe manage.py test --noinput` | PASS: all 19 discovered tests |
| Django: `..\.venv\Scripts\python.exe manage.py check` | PASS: no issues |
| Root: `npm run test:verifier` | PASS: 22 Node proof and browser-script regression tests |
| Root: `npm run test:contracts` | PASS: real isolated EVM authorization, immutable roots, unsupported assurance rejection, supersession/revocation and 7 Merkle tree shapes |
| Root: `.\.venv\Scripts\python.exe tools/test-live-workflow.py` | PASS: 51 checks over real HTTP/PostgreSQL/Web3j/Ganache |
| Root: `.\.venv\Scripts\python.exe tools/test-live-security.py` | PASS: 23 live security checks |

Backend regressions cover uniqueness, invalid-release/nonconsumption, transient suggestions, custom metadata, strict JSON and assurance consistency. A shared 23-case canonical-value fixture checks Java/JavaScript behavior including Unicode, Java whitespace semantics, booleans, dates and large plain decimals. Existing workflow/isolation, encryption, agent replay/revocation, recovery and anchor failure/retry tests remain passing.

Django regressions cover session prevention and legacy/expired cleanup; false/missing/malformed/truthy flags; malformed and noncanonical bundles; cache/export rejection and eviction; local pins without Spring discovery; and custom/derived presentation. Existing CSRF, session-bound export, one-time non-reconsumption and encrypted-cache tests remain passing.

Node regressions require every pin before any RPC, reject identity substitution, malformed signed values and unknown unsigned fields, and still reject a modified fact. Browser-script tests verify failed cryptography never becomes success, malformed/unavailable service status remains separate, revoked policy is visible, and editing pins clears previous independent success.

The existing live suite confirms expiry, concurrent one-time release (one 200 and one 410), revocation, supersession, legacy compatibility, recovery, watcher continuity and Java-to-JavaScript interoperability. It exercises the normal marksheet → five reviewed facts → sixth derived threshold → anchor → selective disclosure flow. The security suite compares a genuine selective bundle against a full fixture disclosure to assert **every hidden fixture value and salt is absent**, tests actual Django sessions and concurrent PostgreSQL registrations, and invokes the separate Node CLI with valid/missing/malformed pins and a tampered proof.

## Browser and operational evidence

The actual browser rendered the recognized threshold with canonical path/type/derivation and the custom lookalike with a prominent holder-authored badge and custom-label prefix. Independent cryptographic verification succeeded with local pins. Clearing the operator pin failed independent acceptance; restoring it allowed a new check. Service policy status was separate. A browser-exported attachment was accepted by the separate Node verifier with explicit local pins.

Local-only screenshots: `docs/screenshots/security-verifier.jpg` and `security-custom-claim.jpg` (excluded from publication because test captures can contain temporary account/link details). Final browser smoke check after the last service restart: PASS for recognized threshold release, independent proof/chain acceptance, separate ACTIVE service status, custom-label distinction and attachment download. The downloaded attachment also passed the standalone Node verifier using the local trust file as the source of explicit CLI pins. Prior browser coverage included real sign-in/upload/review/anchor/composition and one disclosed fact with five private. No successful real phone-width measurement is claimed.

Retained ignored evidence includes `.local-data/final-backend-tests.log`, `final-contract-tests.log`, `final-live-workflow.log`, `final-live-security.log`, `live-test-results.json`, `live-security-results.json`, `demo-session.json` and `security-demo-session.json`. Live tests create disposable fixture accounts/documents; deliberate revoked/expired fixtures should fail verification. Demo links are time-limited and must be regenerated before judging.

During remediation the local EVM became unavailable: Node could not connect and service verification did not accept the proof. Restarting the same persisted chain restored acceptance of a retained active proof. Earlier executable-jar restart evidence below predates the final parser patch; the final jar was built, while live reruns used Maven's normal Spring process. Neither demonstrates distributed-chain resilience.

## Explicitly unresolved / claims boundary

Development key co-location/ACL hardening remains unresolved (audit MEDIUM). LOW findings concerning recovery check/copy races, non-atomic first-seen enrollment snapshots, direct-API production HTTP controls and full deployed-bytecode identity remain documented in SECURITY.md. No exploit resistance for those races is claimed. Session cleanup is logical removal, not forensic erasure of old database pages/backups.

Safe demo claims are limited to salted membership of disclosed canonical facts, platform-signed context, pinned current on-chain credential state, omission of hidden values/salts in genuine selective bundles, and custodial enforcement of release policy. The threshold is a precomputed committed boolean, not a ZK range proof. Neither holder authorization against a malicious platform nor independent issuer authenticity is established. First-seen tracking is only a limited continuity/provenance signal.

---

# Prior implementation validation (historical, before this remediation)

The following earlier measurements are retained as historical evidence. Counts and acceptance wording below do not replace the final remediation results above. Docker, mobile, dependency and optional-AI limitations remain applicable; dependency advisory counts were not re-audited in this patch.

This records local measurements, not paper benchmarks. The cloned baseline compiled but its sole test failed on missing datasource configuration; no working services were listening. The completed workflow was tested using PostgreSQL 17.6, persistent Ganache chain 1337, Java 17.0.19, Spring Boot 4.1.1, Web3j 4.10.3 and Django 6.1. No public network was deployed and no remote repository was pushed.

| Check | Result |
|---|---|
| `mvnw.cmd -B package` | PASS, executable jar; 8 tests, 0 failures/errors/skips |
| `manage.py test dashboard.test_wallet` | PASS, 10 UI boundary tests |
| `manage.py check` | PASS, no issues |
| `npm run test:contracts` | PASS, real isolated EVM deployment/transactions, authorization/state transitions + 7 Merkle tree sizes |
| `tools/test-live-workflow.py` | PASS, 50 assertions through real HTTP/PostgreSQL/Web3j/Ganache |
| Separate Node verifier | PASS on an actual live bundle without original/holder credentials |
| Executable jar restart | PASS, reused same registries, active proof and persistent vault key/original |
| EVM stopped during release | PASS, release failed closed, no facts returned |
| Persistent EVM restart | PASS, unchanged block height/commitments, service and Node verifier accept retained active proof |
| Real browser workflow | PASS, login with CSRF, file upload, five extracted facts/review, sixth derived boolean, anchor, select one fact, create link/QR, public release, independent proof/chain check |

## Cases covered

Merkle tests cover Unicode/decimal/date canonicalization, odd/even/single trees, paths up to 128 leaves, salts/labels/values/index/direction/sibling/root tampering. Workflow tests cover owner isolation, signature checks, encrypted authenticated data, agent signatures/replay/revocation, expiry, consumed/revoked grants, mismatched chain roots and checked backup recovery. An isolated failure test verifies `ANCHOR_PENDING` freezes facts and retry preserves the root. Only these unit tests mock the chain; contract/live tests execute real EVM transactions.

The live HTTP suite demonstrates actual deterministic suggestions and review, first-seen enrollment, cross-account original/provenance denial, absence of hidden values in the released presentation, separate JavaScript interoperability with Java proofs, tampered values/salts/paths/proof siblings/roots/purpose/expiry/provenance/network failure, concurrent one-time release (one 200 and one 410), expired/revoked links, damaged encrypted file detection, verified backup recovery, corrupt backup rejection, changed-history downgrade, revoked agent rejection, atomic on-chain supersession and credential revocation. It runs the real recursive watcher twice across persisted state, changes a nested file, and checks stable file identity/sequence. A preserved legacy upload is anchored and verified through the original registry.

Generated live artifacts stay ignored under `.local-data`: `live-test-results.json`, `live-test-proof.json`, `demo-session.json`, `restart-proof.json`, `restart-results.json`. Retained demo rows are harmless fixtures; proofs created for revocation tests intentionally fail current-state checks. The final demo session points to a fresh active credential/link. Credentials are local fixtures, not committed secrets.

## Browser findings and limits

The composer preview showed one disclosed fact and five remaining private facts. The public page and JSON contained the threshold boolean and no exact `9.17` CGPA, hidden name, institution or birth date. Direct browser verification passed salted inclusion, signed context, active registry state and live policy status separately.

Browser testing found `Referrer-Policy: no-referrer` caused Chromium form POSTs to send `Origin: null`, triggering Django CSRF rejection. `strict-origin` fixed normal forms while omitting bearer paths from referrers. CSRF remains enabled and tested. The in-app browser did not complete the original client-Blob download. Export was replaced by a normal session-bound HTTP attachment of the already released bundle, with an encrypted bounded cache and current-policy verification. The actual browser saved `disclosure-proof.json`, and the separate Node verifier accepted that downloaded attachment. Tests cover export ownership-by-session, one-time non-reconsumption, stale-policy rejection and authenticated cache encryption. API time strings render as readable IST clocks; signed JSON keeps its original ISO/Unix representation.

Screenshots in `docs/screenshots` preserve the actual composer, single-fact verifier and direct-verification result. At the observed 803 px viewport, rendered holder/verifier content had no horizontal overflow. An attempted 390 px viewport override did not change the in-app browser's reported 803 px rendering size; no successful phone-width measurement is claimed. Responsive CSS is present, but real-device validation remains outstanding.

Docker Compose is provided as an alternative, but the installed Docker daemon was unavailable; the tested database route used separate portable local PostgreSQL. Native Ganache µWS acceleration was unavailable for the installed Node build; the JavaScript fallback passed. Toolchain npm audit reported 10 advisories, including one critical; see `SECURITY.md`. Existing optional OpenRouter/legacy AI behavior was preserved but not invoked or claimed as tested wallet functionality.

The PPT/reference paper were inspected but not edited. The repository contains the implementation and documented demo/positioning; no finalized product name, fabricated issuer badge or ZK capability was added.
