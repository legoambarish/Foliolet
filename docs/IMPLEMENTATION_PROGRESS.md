# Implementation progress and final decisions

Preflight on 13 October 2026: verified Git, switched safely to testbuilds, read the complete 72-page report and master prompt, inspected all substantive source/configuration modules and historical evidence, and checked the official PS32 source before implementation. Starting HEAD and unchanged main are recorded in FINAL_VERIFICATION.md. The existing untracked evolution report/output and legacy private data were preserved.

## Integration and migration map

Keep legacy wallet routes/contracts explicitly labeled and unchanged in assurance meaning. Add a new bridge domain package and encrypted generic record table in the isolated demo DB. Retain existing ownership/vault and Merkle primitives. Add governed Solidity alongside frozen legacy contracts, independently pinned registry/governance/code, role desks, private proxy and standalone reader. No automatic assurance migration occurs.

Dependency sequence: isolated foundation/chain seed -> scoped native issuer evidence -> signed verifier requests and browser holder authorization -> direct reader/signed decisions -> optional read-only assistant -> bounded approval executor -> provider/public/NFC extras. Product verification has no AI dependency. Imported fields are not silently transformed into native evidence.

## Recommended seed decisions

Foundation: default local demo identities/passwords and automatic seed, local-only binding, separate persistent data, optional host Ollama. Retain Ganache for compatibility after actual EVM testing; document archived maintenance and audit risk. Do not publish images or invoke remote CI under the user's no-push instruction.

Core: one immutable governance root, claim-type issuer scopes, no arbitrary certification labels, browser holder keys with encrypted export, one-opening grants, retention as recipient commitment, and signed block-specific decisions. Two templates form the hackathon slice. Issuer confirms the CGPA threshold; no ZK claim. External roots never come from the package itself.

Assistant: Spring AI local integration, deterministic source retrieval, exact source-span references, explicit unverified interpretation, bounded fine-print suggestions and owner-only history. Model-written fake quotations are rejected; the final model selects prevalidated spans instead. Optional vision was benchmarked but UI integration cut.

Agent: always show exact human approval; no autonomous mode. Seven-day request ceiling, one opening, one request/credential, no verifier-request creation. Proposal/model aliases cannot widen the selected policy; deterministic typed execution and holder signatures are mandatory. Identical retries/concurrent execution produce one grant.

Integrations: uploaded XML and mock first; Setu only with authorized credentials/stable callback. No authentic sample was available, so unsupported real schemas stay UNKNOWN. Public tunnel requires explicit opt-in; none was exposed. Static NFC stickers remain rewritable/clonable with QR fallback; no hardware claim. Fragment encryption and recorded backup video were cut.

## Phase outcome and acceptance matrix

| Phase | Outcome | Evidence and gap |
| --- | --- | --- |
| 0 | IMPLEMENTED_WITH_RUNTIME_GAP | Native reset/fresh boot/restart pass; Compose config pass; container execution blocked |
| 1 | IMPLEMENTED_AND_LOCALLY_VERIFIED | Real-EVM adversarial suite, live API, role/mobile UI, independent offline reader and simulated pending recovery |
| 2 | IMPLEMENTED_AND_LOCALLY_VERIFIED | Grounding/offset tests, hostile-source read-only API, actual local text/vision benchmarks; optional vision UI cut |
| 3 | IMPLEMENTED_AND_LOCALLY_VERIFIED | Malicious/bypass/cancel/concurrent tests, audit/inline approval, AI-off execution |
| 4 | IMPLEMENTED_WITH_EXTERNAL_GAPS | Mock/XML crypto/XXE, public route isolation and overlay pass; real Setu/tunnel/physical NFC untested |

Machine-derived counts/build/evidence hashes: verification-results.json. Per-phase detail: progress/PHASE_0_COMPLETION.md through PHASE_4_COMPLETION.md. Known P0/P1/P2 items: FINAL_VERIFICATION.md. Exact operator demo and fallback: DEMO_RUNBOOK.md and BACKUP_VIDEO_SCRIPT.md.

## Retained negative evidence and repairs

Docker boot failed on an inaccessible stale socket; automatic approval review rejected removal and no bypass was attempted. This remains an acceptance gap. Initial UI harness selected unloaded options; waits were corrected before the passing browser run. Cross-owner assistant search returned an incorrect 503 until the explicit status handling was fixed. PowerShell 7 converted managed timestamps to DateTime; stop initially refused safely, then parsed both representations and verified PID identity before successful restart. Early model-generated quotations failed exact-grounding checks, motivating bounded prevalidated span references. Direct text benchmark retains one fabricated-quote result and the semantic limits of real quotations. No failed evidence was converted into a success claim.

No inter-phase approval was requested. Final work is local only. There is no production deployment, institutional certification, real provider access or completed recording claim.
