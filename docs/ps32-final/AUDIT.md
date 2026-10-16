# Foliolet PS32 — complete engineering audit

**Assessment date:** 16 October 2026. **Source baseline:** `db55c2c6c1209e567713fa9ab08c5441bd55bc86`. **Implementation branch:** `feature/ps32-final-winning-audit-20261016-1645`.

This report covers the first-party system, its relevant dependencies and operational boundaries. It does not claim exhaustive proof of all code paths or absence of all vulnerabilities. [EVIDENCE.md](EVIDENCE.md) records actual runs, including failures; [SECURITY.md](SECURITY.md) records remediation and residual risks. The final acceptance addendum supersedes intermediate pending statuses without erasing earlier failures.

## 1. Executive engineering decision

Keep the existing Django → Spring Boot → encrypted wallet/PostgreSQL → selective-disclosure EVM architecture for the finale. A clean-slate rewrite would discard unusually valuable working evidence: real independent proof verification, concurrent single-use release, source-bound fact review, lifecycle enforcement and restart recovery. The highest-value changes were trust-boundary repairs, explicit local signature inspection, private session protection, dependency patches and repeatable cross-platform testing—not another token, agent or dashboard.

The product is a **custodial, source-reviewed selective-disclosure wallet**. Its defensible benefit is sharing a selected fact with inspectable provenance and integrity checks instead of forwarding a complete document. Its unresolved limitation is the authority of the underlying claim. A forged original can still produce an internally valid commitment. Nothing in the new implementation disguises that distinction.

The actual source uses Spring Boot 4.1.1, Spring AI 2.0.1, PDFBox 3.0.8 and ZXing 3.5.4. Runtime test inventories, not recalled versions from previous sessions, are authoritative. The security override set is recorded in the POM and final dependency evidence.

## 2. Repository and state safety

The remote DigiLocker HEAD was verified before editing, and a new remote implementation branch was created directly from it. The environment initially could not resolve GitHub. A read-only Actions checkout produced a commit-pinned archive and Git bundle, both hashed and downloaded; an isolated local clone established access to the actual source. Application execution then used disposable GitHub Actions services. This avoided substituting an unrelated laboratory for repository work.

No writes, resets, merges or force-pushes were directed at `main`, `cf` or the source branch. Original PostgreSQL data, vaults, Ganache history, keys, accounts and Ollama models were not accessed or altered. New tests use fictional credentials and fresh state. Original research was recovered from the Library and retained; previous independent experiments are not counted as current tests.

Small commits preserve implementation and failures. `RESEARCH_PROGRESS.md` is the resumption ledger. A temporary branch-restricted literal-patch transport was used to bridge the offline container; it must be removed before final delivery. It was constrained to an exact remote HEAD lease and never executed application code with its write credential.

## 3. Actual end-to-end system

### Acquisition and first observation

DigiLocker-assisted intake is local acquisition assistance, not an approved DigiLocker issuer API integration. The holder establishes a local session and explicitly chosen intake folder. A bounded watcher observes eligible files, records first-seen evidence and submits through the paired private agent boundary. Folder/session expiry, owner binding and limits matter more than the origin branding. A first observation establishes what this system saw at that time; it cannot establish what happened before observation or whether an institution issued the file.

### Original storage and reading

The original is retained byte-for-byte and encrypted through `PrivateVault`; document identity, ownership and version are persisted. PDFBox reads native text and positioned words; Tesseract and complementary local OCR supply rendered evidence. Reader subprocesses, work gates and time/resource limits isolate expensive interpretation from the main service. Plain TXT/CSV remain supported fallback formats. Unavailable OCR or model services must not destroy the original or silently create authoritative facts.

### Suggestions and review

`LayoutFacts`, `FactSuggestions`, `CitationVerifier` and intake jobs associate labels, values, headers and source spans. Suggestions are not immutable truth. `SUPPORTED` describes source support within the implemented checks; `REVIEW_REQUIRED` demands user inspection. The audit repaired cases where a value elsewhere on a page or in a different rotation frame could falsely corroborate a native field. Candidate Name/ID no longer accidentally enter date parsing. Invalid geometry and confidence outside 0–100 are rejected.

The holder confirms facts. Server-side edit tracking distinguishes changes from extraction and prevents the browser from silently preserving an unearned source-support label. Analysis is bound to source hash/version, and stale or modified-source handling is tested. Exact quotation proves that a span occurs; it does not prove correct label/value association, entailment, issuer authority or source truth.

### Commitment and disclosure

Canonical typed claims and random salts form domain-separated Merkle leaves. Internal nodes use the existing ordering and odd-leaf handling. The salted document commitment and root bind the committed version. Solidity restricts state changes to the configured operator and rejects unsupported assurance values. The audit did not alter these encodings, existing salts, credential formats or signature protocols.

A disclosure selects leaves, binds presentation policy and is signed by the platform's custodial key. The recipient receives selected values, their salts and Merkle branches—not the original or undisclosed leaf values/salts. The signed audience/purpose is descriptive policy, not proof of recipient identity. A forwarded bearer link may be used by whoever possesses it unless another identity mechanism is added.

### Verification and lifecycle

Independent JavaScript/Node verifiers recompute canonical claims, Merkle inclusion and presentation signatures against separately provisioned chain/operator/contract pins. Online status checks determine revocation and freshness. The browser's independent result is distinct from the service's own verification response.

One-time release is a POST action under database locking; a GET preview must not consume the grant. Concurrent release, expiry, revocation and supersession are exercised against actual PostgreSQL/EVM services. Session-bound downloads export already released proofs. Copying disclosed information remains possible: revocation prevents future authorized release, not deletion from another person's memory or saved file.

## 4. Trust and authority boundaries

| Boundary | Trusted responsibility | What it does not establish |
|---|---|---|
| Holder browser → private Django | Session authentication, CSRF, explicit review and local workflow | Holder's assertion is not issuer testimony |
| Django → Spring | Numeric loopback, explicit credentials, no environment proxy or redirect, bounded response | Host compromise is not prevented |
| Spring → reader/OCR/model | Bound source identity, constrained subprocess/job resources, no write tools for model | OCR confidence is not factual certainty |
| Spring → encrypted vault | AES-GCM, preserved key, strict paths, bounded originals | Filesystem owner/root compromise is outside the protection |
| SQL → EVM | Operator-authorized commitment and status transitions | Two systems do not form a distributed atomic transaction |
| Platform → verifier | Canonical proofs and custodial signatures | Signature is not holder-held signing or institutional issuance |
| Public receiver → private service | Separate receiver state and allowlisted verification surfaces | Internet deployment was not exercised through a real tunnel here |
| PDF signature → assurance UI | Digest, signature mathematics and current-file coverage of supported formats | No issuer trust anchor/authority or fresh revocation is provisioned |

A local chain is still useful as an independently queryable commitment registry for this demonstration. It is not a decentralized production network. The operator and deployment pins remain a central trust assumption. A conventional transparency log could satisfy many of the same requirements; blockchain is an architectural choice with a demonstrable verification path, not a necessary consequence of privacy.

## 5. Coverage register

“Dynamic” below means an executed test of the named behavior, not every possible path in that module. DTO/entity inspection follows serialization, ownership and persistence boundaries; generated/vendor code is reviewed through dependency provenance and protocol behavior, not exhaustively line-by-line.

| Area and representative implementation | Inspection and executed coverage | Remaining uncertainty |
|---|---|---|
| Auth, `SecurityConfig`, `AuthController`, `UserRepository` | Role/ownership review; Java/Django tests; actual duplicate-user race and database uniqueness; private Origin regression | No production password-guessing/load campaign; account recovery is not a hardened identity provider |
| Wallet `WalletService`, `WalletController`, entities/repositories | Ownership, draft/confirmed/active states, version binding; real HTTP lifecycle and cross-user attacks | Broad production tenancy and long-running migrations not exercised |
| `PrivateVault`, `IntegrityService` | Actual AES-GCM context/tamper, key/ciphertext/backup restart retention, symlink/ID/size/permissions tests; real original recovery | Windows ACL policy, same-user races, crash between file/backup/SQL operations |
| `ClaimCanonicalizer`, `WalletJson`, Merkle/signing classes | Strict malformed/canonical bundle review; Java and Node tests; seven Merkle shapes; nine live tamper variants | Not a formal cryptographic proof or external protocol certification |
| Disclosure service/repositories/controllers | Actual concurrent one-time release, expiry, revocation, supersession, preview and session-bound export | Forwarded bearer links and previously saved facts remain outside revocation |
| Solidity contracts, EVM gateways | Owner access, immutable roots, supported provenance, atomic contract supersession; actual Ganache calls and independent verification | Public-chain gas/finality/reorgs and adversarial consensus not tested |
| SQL/EVM consistency | Pending/retry logic inspected; real chain/database outages and retained-state restart | Crash injection at every transaction boundary and formal reconciliation proof not performed |
| `FoliReader`, positioned text, OCR services/worker | Actual 14-document paired benchmark and eight public receipts; worker tests, missing engines, source hash checks | Diverse genuine Indian academic documents, handwriting and broad multilingual accuracy unproven |
| `LayoutFacts`, `FactSuggestions`, citations | Six independently reproduced baseline failures repaired; exact source spans, rotation/cell/label conflicts; review behavior | Wrong but plausible review suggestions remain; all sources may be forged |
| Intake sessions, agent security, jobs, watcher | Owner/loopback/token/folder/lifetime review; watcher and job interruption tests | No physical desktop event matrix for every browser/filesystem combination |
| Local Foli chat/retrieval/review | Read-only source resolution/citations, bounds, no tool execution; real offline 4B model and real Spring-AI transport | Strict model rubric only 5/10; semantic entailment and broad injection immunity not established |
| Django wallet/intake/Foli views/templates | CSRF, escaped rendering, local private paths, upload bounds, transport tests and actual Chromium flow | Exhaustive DOM fuzzing, accessibility certification and every legacy template not established |
| Sessions/private keys | Encrypted JSON database envelopes, tamper/key fallback/legacy compatibility/CAS migration; real logged-in session after restart | Existing legacy rows need explicit migration; a compromised key still exposes sessions |
| Public receiver, verification JS/RPC bridge | Separate-session/host/origin boundaries inspected; public surface and verifier tests | Actual Cloudflare TLS/tunnel/provider outage and physical mobile/NFC not exercised |
| New signature inspector/UI | Supported real signed/unsigned/tampered PDFs; exact-source binding; private route; actual browser cases | Not issuer verification, all PDF signature profiles, trusted timestamp validation or current revocation |
| Legacy document/AI/case/audit services | Dataflow and authorization review; dangerous cloud egress now default-denied and regression tested | Legacy document storage remains plaintext; do not apply wallet privacy claims to it |
| Windows scripts, Python installers, Compose | Path/PID/state checks; launcher branch bug and JVM bound repaired; platform tests recorded separately | Parsing is not the full Windows PostgreSQL/EVM startup; Compose is database-only |
| Dependency/CI/build | Real locked installs, Java compilation, npm/pip/OSV/Bandit evidence, explicit security updates | Advisory feeds may lag; Ganache bundled advisories remain; no production SBOM attestation |

## 6. Major findings and completed changes

The most consequential correctness issue was false rendered corroboration: a matching OCR value from an unrelated location could contribute to a trustworthy-looking citation. New tests failed against the original code before the production fix and passed afterward. The original 14-document corpus did not expose this defect, demonstrating why a high aggregate score was not enough.

Private transport had inherited Requests defaults. The repaired bridge refuses redirects, ignores ambient proxies, validates numeric-loopback origins and bounds responses. A two-server test proves a 307 cannot forward a private upload body. This is a boundary hardening result, not a claim that an unauthenticated remote attacker could previously choose every upstream URL.

The vault and Django key lifecycle now use owner-only POSIX permissions and avoid replacing existing keys. Source IDs and paths are validated, symlink escapes are rejected and ciphertext allocation is bounded. Authenticated encryption formats are unchanged. Server-side session data now has encryption in addition to Django's outer signature; compatibility and migration preserve IDs and expiry.

The legacy cloud analyzer could send document text even with an empty API key. Rejecting a request at the provider does not undo transmission. It is now disabled before source access unless all three conditions—administrator opt-in, explicit request consent and configured key—are met. Local Foli remains independent of that route.

Additional repairs include bounded Django original uploads, browser-Origin isolation on private Spring APIs, corrected cross-platform test fonts/browser selection/RPC ports, supported local PDF signature inspection and reviewed dependency patch releases. The Windows launcher now recognizes the exact new branch and exposes a bounded JVM heap rather than rejecting the implementation it is supposed to demonstrate.

## 7. Reliability and resource conclusions

The controlled corpus reproduced 168/169 correct unique facts and 168/170 correct suggestions for both baseline and repaired audit code. Zero incorrect automatic suggestions were emitted; two incorrect review suggestions remain. This run preserved extraction performance while closing adversarial assurance gaps. It did not produce a new 99.41%→higher improvement.

Eight real CORD receipts completed with all suggestions requiring review. Narrow held-out grand-total results were 4/6 normalized decimal matches, or 5/6 correct source literals when one unnormalized currency string is included. An identifier was incorrectly associated as a total. These are meaningful negative results and prohibit a claim of universal real-document accuracy.

A real offline Qwen3 4B run passed 5/10 strict answer-and-citation cases. Several failures gave plausible answers with wrong or excessive evidence references; the tested injection canary was not disclosed. A separate actual Spring-AI/Foli transport test passed three focused cases. The model is optional assistance, not the mathematical verification authority. Its observed response times are unsuitable for making every short live-demo action wait on inference.

Actual database interruption originally returned after about 30 seconds. A bounded five-second Hikari connection wait was introduced and is measured in the final acceptance evidence. Restart tests preserve the same chain, vault key, document bytes and existing proofs. This is much stronger evidence than simply stopping and creating a new successful deployment.

## 8. Remaining production blockers

The project is not certified for unattended production with arbitrary public uploads. Priorities are a supported chain runtime and remaining supply-chain remediation, workload-wide upload/rate limits, OS-level reader isolation, hardened deployment/secret management, verified issuer authority policies, schema-specific real-world datasets, stronger user authentication and audited backup/reconciliation procedures. No new credential standards adapter or ZK system should be rushed into the finale.

Legacy plaintext routes should be removed or clearly segregated before any broad confidentiality claim. Genuine holder-controlled keys and standardized presentations are future architectural changes requiring migration, not labels to add to the current implementation. Full private-session encryption protects a stolen database without the key; it does not make the platform noncustodial.

The relevant finale question is not whether Foliolet is an entirely new cryptographic invention. It is whether the working workflow makes over-disclosure visibly avoidable, separates trust assertions honestly, rejects tampering and survives realistic failures. The committed code and evidence now provide a credible demonstration of that narrower proposition.
