# PS32 final audit — durable execution ledger

## Scope and safety

Assignment received 2026-10-16. The entire 807-line master prompt was read. Work only on `feature/ps32-final-winning-audit-20261016-1645`; never merge into or modify `main`, `cf`, or the source branch. Original runtime state has not been accessed or changed. All test services/records are disposable.

## Verified source and working environment

Source HEAD `db55c2c6c1209e567713fa9ab08c5441bd55bc86`, tree `75e3b538a1e04b5a71fbbfc0dc644764d4403de8`, parent `6db30e1520211b0dae88c8b47200a9ed1b6089c7`. The new remote branch was created directly at that exact source commit.

Direct container DNS prevented GitHub cloning. This was overcome using a commit-pinned GitHub Actions archive and Git bundle, downloaded through the GitHub connector and cloned into an isolated local directory. Both SHA-256 checks passed. This is the actual complete repository, not a substitute lab. Local snapshot `0627643118c28fc3bdedc4b2d8705d4d48739ea7` has unchanged baseline application source. Snapshot run: https://github.com/legoambarish/Foliolet/actions/runs/38935130981 . Actual application builds run in isolated GitHub Actions; local networked Maven compilation has not been claimed.

## Preserved previous research

Recovered `Foliolet_PS32_Research_Test_Recovery_Package.zip` from the user's Library into isolated storage, without changing the original. Earlier independent laboratory results are not this branch's results. Existing repository reports remain inherited unchanged.

## Executed baseline — PASS

Run https://github.com/legoambarish/Foliolet/actions/runs/38934429615 at `d610a5e3d2e240c5f36d406503b9866ad4711b86` (baseline source plus audit docs/workflow):

- Ubuntu 24.04.5, Temurin Java 21.0.12, Python 3.13.16, Node 22.23.3, Tesseract 5.3.4.
- Java: 108 tests; zero failures/errors/skips; 98 main sources compiled.
- Django: 74 tests PASS; framework check no issues.
- Node verifier: 22 tests PASS.
- Solidity script: PASS, including authorization, immutable roots, unsupported assurance rejection, atomic supersession, revocation and seven Merkle shapes. No invented assertion count.
- `pip check`: PASS.
- Artifact ID 12060885684 downloaded and preserved locally; durable summaries are required because Actions artifacts expire.

## Dependency findings — unresolved

Spring-side npm reported 39 advisories: 2 low, 9 moderate, 23 high, 5 critical. Root npm was clean. Ganache's bundled transitive dependencies contribute; assess reachability rather than assuming every advisory is remotely exploitable. `npm audit fix --force` proposes a Ganache downgrade and is not an acceptable blind fix. Ganache's unavailable native uWS module falls back to Node successfully.

## First production corrections

Eight independent regression tests added in `SourceAssociationRegressionTest`, commit `f5b0ed977b9e0fdc09cb08541086c7249cd911ee`:

1. `Candidate Name` / `Candidate ID` accidentally match `contains("date")` and acquire date uncertainty.
2. A matching OCR value elsewhere on the same page can falsely corroborate native evidence.
3. A conflicting rendered label can still earn an OCR-corroborated citation label.
4. Off-page/overflowing word geometry and finite confidence outside 0–100 are accepted.

Production corrections: `dcfd3a5b1f2660d5b1fc4ec2ed698a3d4429bb6c`. Corroboration now requires the same physical cell/frame and matching label/value; geometry and confidence bounds are stricter; date labels use word boundaries/explicit aliases. Credential formats, keys and commitment canonicalization are unchanged. Post-fix execution is still pending; do not mark these cases green without retrieved evidence.

A temporary branch-restricted workflow transports reviewed local patches. It checks the index and an exact branch-HEAD lease, executes no application code with its write credential, and fast-forwards only the isolated branch. Remove this privileged transport workflow before final delivery; retain patches as provenance.

## Further audit findings under investigation

`PrivateVault` defaults key/state file permissions and checks read paths lexically rather than against symlinks. The general Django wallet proxy lacks Foli's loopback-only origin validation, environment-proxy isolation, redirect refusal and bounded reads. Holder Basic credentials are retained in server-side sessions. These findings need targeted reproduction/remediation; receiver sessions are separate and released proof bodies are encrypted.

## Research progress

Organizer overview independently retrieved: 17–18 October 2026, metadata 09:00 Oct 17 through 15:00 Oct 18 while marketing says 24 hours. Exact PS32 tracks page live fetch currently fails; preserved earlier research is being rechecked. No numerical rubric or prebuilt-code rule established in this run. W3C VC Data Model 2.0 and RFC 9901 independently retrieved. DocLayNet and CORD official repositories and licenses located. No fresh real-world document accuracy result yet. Hosted sensitive-document processing is not enabled or authorized.

## Remaining work

Reproduce and verify fixes; complete relevant module/trust-boundary coverage; harden storage/proxy; execute PostgreSQL/EVM/browser workflow; benchmark synthetic and legally licensed held-out documents; resource, outage and restart tests; finalize challenge/issuer/competitor research, deployment guides, claims, judge defense and readiness report.

Preserve commands and failures. Unit tests alone do not establish browser-to-proof readiness, issuer authenticity or universal OCR accuracy.
