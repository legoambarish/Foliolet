# Security and adversarial report

Read with [AUDIT.md](AUDIT.md), [EVIDENCE.md](EVIDENCE.md) and the final acceptance addendum. Severity is an engineering prioritization for this product, not an invented CVSS score. “Fixed” means the specified behavior is repaired and covered; it does not mean the whole class of attack is impossible.

## 1. Threat model

Protect private originals, selected-versus-hidden claims, holder sessions, encryption/signing identities and the integrity of verification decisions. Adversaries include a malicious uploader, a holder falsifying their own document, a recipient editing a proof, a bearer-link holder racing another recipient, a hostile web origin, an unreliable OCR/model output and a local filesystem actor with access below the intended private boundary. A compromised operating-system administrator or the custodial backend with its keys is not excluded by cryptography alone.

The public receiver must not become an authenticated private API proxy. A valid proof must not be represented as issuer truth. Dependencies going offline must not turn into cached success. Expiry must not be described as erasing previously disclosed information.

## 2. Findings and remediation

| ID / priority | Reproduction or evidence | Implemented correction | Qualification |
|---|---|---|---|
| SEC-01 / P0 assurance | Six baseline failures in `SourceAssociationRegressionTest`, including wrong-location/rotation/label OCR corroboration | Require same physical cell/frame and label/value; reject invalid geometry/confidence; distinguish actual date labels | Source support still does not prove issuer truth or semantic correctness |
| SEC-02 / P0 privacy | Legacy analyzer executes HTTP request with source text even when provider key is empty; mocked transport test demonstrates the attempted send | Default-deny before DB/source/network; administrator switch + explicit per-request consent + nonempty key; bounded/no-redirect provider client | No live private document was sent to demonstrate this defect; external mode was never enabled |
| SEC-03 / P1 transport | Requests defaults allow redirect following and ambient proxy configuration; actual two-loopback-server 307 test | Numeric-loopback-only origin, `trust_env=False`, no redirects, streamed size limits, controlled errors | Upstream origin was configuration-controlled, not a proven arbitrary unauthenticated SSRF parameter |
| SEC-04 / P1 vault | Actual symlinked files/parents/key, path traversal IDs, oversized ciphertext and permissive POSIX mode tests | Strict IDs; real-path/NOFOLLOW containment; owner-only storage; bounded reads; CREATE_NEW key preservation | Same-user/root compromise and Windows ACLs remain separate trust assumptions |
| SEC-05 / P1 sessions | Server-side signed JSON contained reusable Basic credentials without confidentiality | AES-GCM JSON inside existing signed envelope; separate context-derived key; legacy compatibility and explicit CAS migration | Host and key compromise still expose credentials; unrewritten legacy rows remain readable |
| SEC-06 / P1 upload DoS | Declared oversize and forged size metadata tested | Reject above 20 MiB before read; bounded read at limit+1; unchanged valid bytes | A per-file bound is not global rate/connection/multipart ingress limiting |
| SEC-07 / P1 private API CSRF boundary | Browser Origin with cached Basic credentials; real authenticated HTTP requests | Reject browser Origin/cross-site metadata on private Spring routes; keep Django CSRF-protected bridge | Native clients remain explicitly credentialed; not a replacement for authentication or loopback binding |
| SEC-08 / P1 failure latency | Actual database stop caused approximately 30-second response | Configurable five-second connection acquisition timeout | Database statement timeouts and all outage percentiles are not established by this one measurement |
| SEC-09 / P1 misleading signature interpretation | Real signed, unsigned, tampered and source-substituted PDFs | Hash-bound private inspection separates digest, signature math, current-file coverage and issuer uncertainty | No `ISSUER_VERIFIED` state, trusted issuer roots or fresh revocation evidence is provided |
| SEC-10 / P1 supply chain | Actual pip/npm/OSV results; publisher advisories below | Patch Django/urllib3, Jackson 2/3, BC, OkHttp/Okio and Tomcat; rerun resolved dependency and application tests | Final audit results determine remaining matches; a green feed is not a warranty |
| SEC-11 / P1 demonstration | Windows startup guard accepted only DigiLocker-named branches | Permit the exact new audit branch, preserve other guards, default JVM maximum heap 768 MiB | Launcher parsing is not complete Windows hardware acceptance |

SEC-01's production correction is `dcfd3a5b1f2660d5b1fc4ec2ed698a3d4429bb6c`; SEC-03 is `3bdf6d59b5683904a83b977812fd639f87f720e3`; SEC-04 is `193a287417da68e931909fc0c3359be80f7913fe`. The committed implementation history in final evidence identifies all later component commits. New tests are retained even when their first run failed.

## 3. Cryptographic and lifecycle review

The existing domain-separated Merkle encoding, canonical claims, random salts and presentation format are unchanged. Canonical parsing rejects malformed or nonconforming structures rather than silently reinterpreting a proof. Verifiers recompute selected-leaf hashes and roots, check signatures against independently provisioned pins and query applicable chain state. Actual contract tests cover owner-only transitions, immutable roots, supported provenance, revocation and supersession. Actual live tests mutate values, labels, types, commitments, signatures and other proof components; positive controls remain valid.

One-time links release through POST and a transactional lock; the real concurrent test establishes one successful release in its exercised race. GET preview and link scanners are not supposed to consume a grant. Session-bound proof export does not grant a different session access to an already released bundle. Expired, revoked and superseded credentials fail the tested policy checks.

These properties do not authenticate whoever received a forwarded bearer link. A disclosure's audience string is not a recipient login. A platform EIP-191 signature is custodial platform authorization, not a holder's hardware-key signature. Merkle inclusion establishes commitment membership, not eligibility truth or a zero-knowledge threshold relation.

The original, SQL records and EVM state do not participate in one distributed transaction. Pending states and retries reduce inconsistent outcomes but need production reconciliation/outbox work. Restart tests preserve existing state rather than reinitializing a fresh successful chain. Chain identity mismatch or unavailability must fail closed. An offline proof can establish mathematical consistency under cached pins, but cannot establish that no new revocation occurred while offline.

## 4. PDF/AI boundaries and remaining attacks

The document reader and signature inspector are not general-purpose execution environments. Source files, native text, OCR output, QR contents and model text are untrusted. No model tool is authorized to change grades, enroll documents or anchor credentials. Evidence quotation is validated against source text; final fact confirmation and verification remain deterministic application decisions.

The new signature worker uses a private temporary file, bounded input/output, a parent timeout, one in-process concurrency slot and POSIX CPU/address-space limits. It disables network fetching and connection calls; the Python restriction is defense in depth, not an OS sandbox. The real local-model experiment separately used an OS network namespace containing only loopback, a stronger demonstrated no-egress condition for that experiment.

Signature mathematics is evaluated without implicit trusted roots. The library's `soft-fail` revocation context is used only to permit mathematical inspection when no revocation source is provisioned; the report explicitly says `revocation=NOT_ESTABLISHED` and `issuerVerified=false`. It is not used to accept an issuer credential. A source hash mismatch, unsupported format, timeout or incomplete check never becomes issuer verification. A self-created certificate can pass signature mathematics while remaining untrusted; that is deliberately demonstrated.

Remaining concerns include decompression/rendering bombs within allowed file sizes, global concurrent-worker pressure, long OCR latency on different hardware, unusual incremental-signature structures, handwritten/multilingual layouts, model semantic errors and same-user filesystem races. The eight public receipt cases produced a wrong total association despite exact source fragments. Review-required status is necessary but does not turn a wrong suggestion into a correct one.

## 5. Dependency and static-analysis evidence

The original Spring-side npm install reported **39 advisories: 2 low, 9 moderate, 23 high and 5 critical**, substantially involving Ganache/bundled dependencies. Root npm was clean. The proposed blind `npm audit fix --force` downgrade was rejected. Ganache remains a loopback development dependency with unresolved production suitability. Do not expose its RPC as an unrestricted public blockchain service.

The later pip audit found nine advisory matches for Django 6.1 and two for urllib3 2.7.0. The implementation pins Django 6.1.2 and urllib3 2.8.0. Publisher guidance: [Django 6 October security releases](https://www.djangoproject.com/weblog/2026/oct/06/security-releases/) and [urllib3 2.8.0 release](https://github.com/urllib3/urllib3/releases/tag/2.8.0). The urllib3 patch addresses malformed compression/chunk handling; this is relevant to robust bounded network clients even though this application normally talks to loopback.

Resolved Java dependencies originally included advisory matches in BC 1.73, OkHttp 4.9.0/Okio 2.8.0, Jackson 2.21.5/3.1.5 and Tomcat 11.0.23. Reviewed security overrides move to BC 1.84, OkHttp 4.12.0/Okio 3.6.0, Jackson 2.21.7/3.1.7 and Tomcat 11.0.26 without changing the Boot/AI major line. Sources include [BC release guidance](https://www.bouncycastle.org/resources/new-releases-bouncy-castle-java-1-84-and-bouncy-castle-java-lts-2-73-11/), [Jackson forward-reference advisory](https://github.com/FasterXML/jackson-databind/security/advisories/GHSA-cxp5-3px4-pw24), [Tomcat security notes](https://tomcat.apache.org/security-11) and [official release history](https://tomcat.apache.org/oldnews.html).

Advisory counts are not exploit counts. Some Tomcat findings depend on examples, RewriteValve, clustering, WebSocket, HTTP/2 or TLS configurations not observed in the local demo. Some Jackson findings require specific parser/identity modes. Rather than assuming all were unreachable, reviewed patch versions were applied and actual protocol tests rerun. Final resolved-version results are authoritative; feeds can lag vendor disclosures.

Bandit produced 61 findings, mostly assertions and subprocess use in test/installation tools. Four high-severity `tar.extractall` warnings occur in the installer after path, traversal and link validation. Static inspection found existing prevalidation, so those warnings are not four demonstrated code-execution vulnerabilities. Archive size/decompression exhaustion remains a distinct question. The report does not suppress the raw scanner output or equate tool warnings with verified attacks.

## 6. Migration and operational safety

Do not regenerate `vault.key`, Django keys, relay identity, deployment pins or chain state to make a failing test pass. New key creation uses exclusive creation and reads an existing valid key. The session migration is explicit:

```text
python manage.py reencrypt_sessions --dry-run
python manage.py reencrypt_sessions
```

Back up the relevant private database and keys before a real deployment migration. The command preserves session identifiers and expiry, skips invalid rows rather than guessing their contents, and uses compare-and-swap to avoid overwriting concurrent changes. It does not rotate keys or clear sessions automatically.

The public receiver uses separate key/session storage. Legacy document storage remains plaintext and must not be included in the wallet's encryption claim. The cloud analyzer remains disabled. Debug servers, trusted local PostgreSQL fixtures and Ganache are demonstration infrastructure, not a recommended internet deployment.

## 7. Residual risk register

P0 for any presentation: never imply issuer verification, zero-knowledge eligibility, fully decentralized operation or guaranteed AI correctness. No new P0 bypass reproduced in this run is knowingly left unfixed in the tested demo path; that is not proof that none exists.

P1 before production: replace or tightly contain unsupported/advisory-bearing Ganache dependencies; verify real issuer trust policies and revocation; production identity/session design; global resource/rate limits; hardened OS-level document isolation; formally rehearsed backup/reconciliation; remove or segregate legacy plaintext routes.

P2: workload latency distributions, fault injection at all SQL/EVM/file boundaries, key rotation with explicit re-encryption, standardized credential interoperability, independent holder consent signatures, comprehensive Windows ACL and macOS acceptance, multilingual/schema-specific held-out datasets.

The strongest judge-facing security demonstration is a truthful rejection: a changed proof fails, a changed signed original fails its digest, a valid self-signed document still does not become an authenticated institutional credential, and a dead chain/database does not produce a green verification result.
