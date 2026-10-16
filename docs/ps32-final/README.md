# Foliolet — PS32 final engineering delivery

**Implementation branch:** [`feature/ps32-final-winning-audit-20261016-1645`](https://github.com/legoambarish/Foliolet/tree/feature/ps32-final-winning-audit-20261016-1645)

**Verified source baseline:** `db55c2c6c1209e567713fa9ab08c5441bd55bc86` from `feature/digilocker-assisted-intake`. No writes or merges were made to `main`, `cf` or the source branch, and no original private runtime state was touched.

Start with [FINAL_ACCEPTANCE.md](FINAL_ACCEPTANCE.md) for the latest actual results, then [CLAIMS_READINESS.md](CLAIMS_READINESS.md) for the release boundary. The conclusion is a controlled local demonstration, not universal issuer verification or production certification.

## Deliverables A–L

| Requirement | Committed deliverable |
|---|---|
| A. Complete technical audit | [AUDIT.md](AUDIT.md): real components, dataflow, trust boundaries, module coverage, limitations |
| B. Implemented fixes | Application/test changes on this branch; [SECURITY.md](SECURITY.md), [EVIDENCE.md](EVIDENCE.md), [FINAL_ACCEPTANCE.md](FINAL_ACCEPTANCE.md), and the [commit history](https://github.com/legoambarish/Foliolet/commits/feature/ps32-final-winning-audit-20261016-1645) |
| C. Research report | [RESEARCH.md](RESEARCH.md): official PS32, competitors/standards, issuer trust, datasets and individual-accessible options |
| D. Document-intelligence evaluation | [EVIDENCE.md](EVIDENCE.md), [evidence-summary.json](evidence-summary.json), `tools/ps32-benchmark.py`, `tools/ps32-public-corpus.py`, controlled benchmark workflow |
| E. Architecture recommendation | [ARCHITECTURE_ROADMAP.md](ARCHITECTURE_ROADMAP.md), supported by [AUDIT.md](AUDIT.md) |
| F. P0/P1/P2/P3 roadmap | [ARCHITECTURE_ROADMAP.md](ARCHITECTURE_ROADMAP.md): completed, deferred and rejected work, ordinal impact/effort/risk |
| G. Security/adversarial report | [SECURITY.md](SECURITY.md): reproduced defects, actual remediation, remaining attack boundaries |
| H. Complete testing evidence | [EVIDENCE.md](EVIDENCE.md), [FINAL_ACCEPTANCE.md](FINAL_ACCEPTANCE.md), [evidence-summary.json](evidence-summary.json), linked Actions runs and retained test code |
| I. Windows/cross-platform demonstration | [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md): exact branch setup, dependencies, health, shutdown, preservation and platform limitations |
| J. Grand-finale preparation | [JUDGE_DEFENCE.md](JUDGE_DEFENCE.md): presentation strategy and 33 skeptical questions with implementation-bound answers |
| K. Claims register | [CLAIMS_READINESS.md](CLAIMS_READINESS.md): confident, qualified and prohibited claims |
| L. Final readiness verdict | [CLAIMS_READINESS.md](CLAIMS_READINESS.md) and latest [FINAL_ACCEPTANCE.md](FINAL_ACCEPTANCE.md) |

## What changed materially

The audit repaired false OCR corroboration and invalid evidence geometry; hardened private HTTP transport, vault paths/permissions and original-size limits; encrypted server-side sessions with compatible migration; blocked legacy silent cloud egress by default; enforced private browser-Origin boundaries; added bounded local PDF-signature inspection without inventing issuer authority; patched reviewed dependencies; repaired the new-branch Windows launcher; and exercised the actual database, chain, browser and retained-state recovery.

The historical OCR hotfix's synthetic accuracy was independently reproduced and preserved, not exaggerated into a new improvement. Genuine held-out receipts and actual offline local-model evaluation exposed important failures, all retained in the evidence. Passing source-fragment validation is not the same as correctly associating a field or establishing issuer truth.

## Evidence and provenance

Tests execute the real repository in isolated services. Source recovery through verified Git archive/bundle avoided the container's DNS limitation. Earlier Library research was preserved, not substituted for current application tests. Each report distinguishes static review, dynamic tests, mocks, actual services and unsupported environments.

Actions artifacts expire after 14 days; the committed reports, compact machine-readable results, test code and exact run/commit identifiers remain durable. Failed runs are intentionally recorded. A later successful run does not erase an earlier defect or justify claiming a test that never executed.

The temporary privileged patch-transport workflow was removed at `d2d5fa7415cb4a0d11ed761bb6cf0ac9cec6d069`. Remaining evidence workflows use read-only repository permissions. No private keys, bearer tokens, original user documents or model weights belong in this delivery.

## Presentation boundary

The critical demonstration should use a clearly fictional native PDF, source review, confirmation, Merkle anchoring, selected disclosure, independent verification and deliberate tamper rejection. The signature demonstration should show that valid mathematics can coexist with an untrusted issuer. Keep optional local AI and physical NFC off the critical path unless rehearsed on actual hardware.

The strongest honest message is **“Share the fact, not the file—and see exactly what has been verified.”**
