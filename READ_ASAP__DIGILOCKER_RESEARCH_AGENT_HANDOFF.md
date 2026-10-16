# READ ASAP — Foliolet PS32 research-agent source-access blocker and continuation instructions

**URGENT / ACTION REQUIRED — 16 October 2026**

This file is a durable handoff to the GPT-6 research/engineering agent. **The goal is to WIN Hack Sprint PS32 by finishing a reliable, honestly verified product.** Continue the existing work; **do not redo completed research**.

## Critical branch identity and availability

- Repository: `legoambarish/Foliolet`.
- **Authoritative implementation baseline (user-reported local Git branch):** `feature/digilocker-assisted-intake`.
- **Authoritative target commit (user-reported):** `8e6671003c090dc958ce718afa12484c5e47299b`.
- **That branch was originally created from:** `cf` at `b053b324e87d4a90f4d0151d3f7e7077759a89c5`.
- User-reported Windows checkout: `C:\Users\User\Downloads\Foliolet-digilocker-intake`. This path is **not accessible** to cloud agents merely because it is written here.
- **Observed on the GitHub remote on 16 October 2026:** the DigiLocker feature branch is absent, and its target SHA is not resolvable. Available branches were `main`, `cf`, `codex/foliolet-evidence-bridge`. Recheck these observations rather than assuming they are permanently true.
- **This handoff branch is documentation only, based on `cf`.** It is **not** the authoritative DigiLocker code and must NEVER be treated as a substitute for the user-reported feature branch.

### Next safe action

1. Check the working environment for a **mounted local checkout, uploaded source ZIP, source archive with commit manifest, or Git bundle**. If the actual user checkout is accessible, inspect its `git status`, branch name and commit SHA before any write.
2. If not accessible, look for a newly shared/authorized private remote branch or attachment. A source ZIP can unblock code inspection, but lacks Git history; do not claim verified ancestry from ZIP contents alone. A Git bundle or authorized push of the feature branch can preserve ancestry.
3. **Only after obtaining the real DigiLocker baseline**, create a NEW isolated implementation branch from it. Never edit/push `main`, `cf`, or `feature/digilocker-assisted-intake`. Preserve all existing working trees, uncommitted changes, database state, encryption keys, private documents, models and run artifacts.
4. If source access remains blocked, persist the completed research, reproducible standalone experiments, benchmark plan and blockers without pretending to have implemented or tested the target branch. State the exact missing artifact. **A note in this repo does not make a local checkout remotely accessible.**

## Carry forward research already performed

The agent's last reported work:
- Read the full assignment, investigated workspace/checkout/branch and the failure PDFs.
- Prepared extraction and benchmark experiments and a safe handoff.
- Identified possible **evidence-validation and OCR-completeness flaws in an accessible ancestor**; these **have not been confirmed in the DigiLocker implementation**.
- An alternative extraction technique increased recall but accepted a character-confusion error. **OCR confidence alone is not sufficient** to establish reliable source-backed facts.
- Browser access and the exact local feature branch were unavailable in that run. Preserve those observations and all associated evidence; do not restart the entire research.

## Required problem to solve in the REAL branch

Observed user-visible failures (copy/reproduce accurately):
- `No verifiable fields found · enter facts manually`.
- `1/2 pages readable · 1 OCR pages · 0/2 pages inspected for indicators`.
- `2/2 pages readable · 2 OCR pages · 2/2 pages inspected for indicators` but still **no verifiable fields**.
- `No unambiguous label/value lines were found.`
- Separated columns/table cells and potentially corrupted reading order.
- Low-confidence OCR on pages 1 and 2.
- DigiLocker visual/logo OCR unavailable or unreadable; indicator searches incomplete.

Diagnose **each stage independently**: PDF object/text extraction and rendered page fidelity; per-page OCR, image orientation and layout; table/key–value association; QR decoding and visual indicators; model prompt/context/schema; model response; strict field canonicalization; source span/citation evidence matching; fact review UI; coverage and ambiguity reporting. Locate where fields are **lost, misread, falsely accepted or discarded**, with instrumented evidence and reproducible before/after tests. Do not assume the LLM is the sole cause.

## Execution requirements once source is available

- Research the official PS32 statement, relevant prior work and realistic individual-accessible methods. **No government/organization API approval as a prerequisite**.
- Test on appropriately licensed, safe **real-world document datasets**, and synthetic/adversarial examples; distinguish results. Include Indian academic layouts where legally available.
- Benchmark local models and genuinely free, individually accessible options (e.g. Gemini/Groq/NVIDIA, subject to verified current terms). Sensitive/private source bytes must **not** go to third parties without explicit informed consent. No secretly paid services.
- Maintain truthful source badges: logo/QR, watcher observations, and unchanged AI suggestions are not issuer authentication; do not invent issuer signatures or ZK guarantees.
- Complete a systematic whole-repository audit, prioritize fixes, implement necessary changes and regress full affected workflows (wallet, crypto, API, security, receiver, NFC/share, OCR and AI). Confirm results against the ACTUAL feature branch.
- Maintain a recovery/progress document with branch/base identification, completed findings, pending tests, instructions, failures and limits. **Commit completed steps regularly to the NEW branch**, never leak secrets/private user documents into Git. Push only the new authorized branch if remote access is available.
- Deliver code + verified tests + reproducible real-document benchmark + Windows setup/demo instructions + architecture/limitations + difficult judge questions + final readiness verdict.

**Do not silently fall back to older `main`/`cf` when the user expressly required the DigiLocker branch. Do not stop after a plan; perform independent work whenever possible, and make the source blocker explicit if it truly prevents further implementation.**

### Why this handoff exists

The user asked for an in-repository **READ ASAP** clarification so the next agent can discover and update its own research plan without needing to repeat a large conversational prompt. This file carries information and instructions only. It neither supplies the missing local checkout nor proves the agent is reading it automatically.
