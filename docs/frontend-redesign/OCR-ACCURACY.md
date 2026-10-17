# Frontend branch extraction repair — 18 October 2026

Implemented and tested in `C:\Users\User\Downloads\Foliolet-frontend-redesign`, on `design/frontend-refresh-20261017`.

The starting branch was `620c6700634ff96a17b4d4f5cceb72ad16f820a2`. Local main remains `c40cc729b36fb6ac9d18bb8aea7d295a4e2ff6b2`. No merge, push, public deployment or tunnel was performed. Changes are in this branch's working tree. Test services used a separate local database, vault and chain, with fictional accounts/documents; they were stopped afterward.

## Finding

The starting branch's Spring OCR/intake code and `intake.js` were **identical to main**. The earlier P0 extraction fixes were already merged. There is no source evidence of a model-version downgrade during the frontend redesign. The defects below were inherited extraction and review-flow limitations.

| Defect | Correction |
| --- | --- |
| OCR delimiter fields outside a short academic/identity whitelist were rejected. | Explicit, structurally bounded labels now work across other field kinds, including invoice/customer/policy references, addresses, contacts and identifiers. Adjacent separate delimiters work too. Literal characters and leading zeros are preserved. |
| Forty fields were silently the effective extraction ceiling despite the wallet accepting 64. | Extraction uses the wallet's 64-fact capacity. Overflow produces an explicit warning and partial result; the wallet/proof limits were not expanded. |
| One successful structured field disabled fallback linking for the entire document. | Only plausible unresolved pairs enter the local linker, alongside deterministic results. Consumed fields, rejected table cells, weak tokens and redundant OCR checks cannot re-enter through the model. |
| Free-form JSON let the local model invent source-cell IDs. | Generation uses a JSON schema enumerating the available cell IDs, followed by the existing same-source, adjacency and exact-fragment validation. Models still cannot supply field values. Linking has a shared 15-second/two-chunk budget; pairs cannot be split across chunks. |
| A high page-average OCR confidence concealed a weak identifier or score. | A weak alphanumeric value can trigger one independent local RapidOCR check, bounded to eight seconds within the existing OCR deadline. No letter/digit correction is guessed. This recovered a fictional vehicle identifier that Tesseract consistently misread. |
| Discarded orientation trials could become candidate fields or trigger unnecessary inference. | The selected OCR orientation determines field discovery. Other trials stay in the retained snapshot; they do not create extra associations. |
| Right-aligned marks could be assigned to the next column; printed absent-status codes disappeared. | Column containment is checked before nearest-header association. Explicit status tokens such as `AB` remain literal text for review rather than becoming a guessed numeric mark. |
| Meaningful label prefixes and non-Latin/long label paths could collide or be lost. | Common semantic prefixes such as “Previous School” are retained. Non-Latin labels get stable ASCII field paths, and long paths receive a distinguishing hash suffix. This tests path handling, not universal multilingual OCR. |
| An empty reread restored the old baseline; server-rendered rows also used old results. | An explicit empty current result stays empty. Both browser and server rendering prefer the latest result while preserving the immutable original comparison baseline. |
| Rereads with unsaved edits left old review cards on screen. | Existing edits stay intact, latest review evidence refreshes, and duplicate paths cannot be added from review cards. Stale scan notes are cleared from blank rows. |
| Complete negative indicator checks appeared indistinguishable from unavailable checks. | Local labels distinguish `NOT_DETECTED`, `INCONCLUSIVE`, `NOT_CHECKED`, success and failure. Signed v1 disclosures retain their existing state vocabulary; local absence maps conservatively to `INCONCLUSIVE` there. No proof format changed. |

Extraction is versioned as `foli-pages-4-field-confidence`; fact suggestions as `intake-facts-4-broad-fields`. The local Qwen model and pinned OCR weights were not replaced. All OCR-only/model-linked fields still require explicit review. QR, branding, watcher provenance, fact lineage, signature integrity and issuer authority remain separate signals.

## Measured comparison

[OCR-METRICS.json](OCR-METRICS.json) contains per-document hashes, results and timings. The corpus has 18 fictional documents and 243 explicit golden fields: the existing 14 PDF adversarial/layout fixtures plus broad native/scanned forms, distinct school labels and a 48-field text record.

Baseline classes were retained before edits. Each before/after pair reads identical bytes with the same local tools. Values count as correct only when both their field path and complete canonical value match the golden record. Every emitted suggestion is included in precision, including suggestions requiring review.

| Metric | Unchanged branch | Repaired branch |
| --- | ---: | ---: |
| Correct facts / labelled targets | 220 / 243 | **242 / 243** |
| Exact fact recall, including review | 90.53% | **99.59%** |
| Precision across all emitted suggestions | 98.65% (220/223) | **99.18% (242/244)** |
| Incorrect automatically populated fields | 0 | **0** |
| Median total reading/extraction time | 4,091.5 ms | **4,086.5 ms** |
| Slowest document | 32,553 ms | **10,290 ms** |
| Broad scanned form, correct fields | 0 / 12 | **12 / 12** |
| Broad scanned form, total time | 32,553 ms | **7,217 ms** |

The two remaining incorrect proposals are **review-only**: a native value that conflicts with the rendered page, and a printed `9O` read as `90`. Neither is automatically accepted. All **954 emitted label/value/header fragments** exactly match their UTF-16 source offsets. Exact source binding does not by itself prove correct OCR.

The 18 repaired structured cases needed **zero model calls**. A separate unfamiliar-label PDF was tested with the real local Qwen model: the deterministic name and model-linked award code were both correct in **3/3 runs**. Linking took **2,245–2,810 ms**, and total reading plus linking took **4,536–5,748 ms**. The original unconstrained model attempt returned an invalid ID and was rejected; that failed evidence is retained locally.

Timings are observed single runs per document/version, with cold benchmark JVMs and a shared local model; they are not statistical latency guarantees. Median latency was effectively unchanged. The two rotated scans spent approximately 3.3–3.6 extra seconds on independent OCR validation, despite the lower overall maximum. The stronger accuracy check has a bounded cost on some documents.

## Verification

| Check | Result |
| --- | --- |
| Full Java tests and packaged JAR | 157 discovered: **153 passed**, 4 platform skips, 0 failures/errors |
| Django dashboard suite | 119 discovered: **118 passed**, 1 skip |
| Node proof, verifier UI and QR suites | **23 passed** |
| Actual isolated EVM contract gate | Passed authorization, immutable roots, lifecycle checks and seven Merkle shapes |
| Offline OCR dependency/hash/network boundaries | **4 passed** |
| Controlled-API Edge tests using this branch's real templates/assets | **7 passed**: empty reread, baseline preservation, fresh evidence with retained edits, duplicate prevention, label state transitions, escaping, phone/desktop and light/dark layouts |
| Actual branch Spring/PostgreSQL/vault/Django/Edge walkthrough | **6 passed**: native/scanned upload, original-page preview, reread, explicit OCR acceptance, server-confirmed unchanged/edited lineage, no external requests or JavaScript errors |
| Live local Qwen source linking | **3/3 runs**, exact expected values, one constrained model call per run |
| Final-source replay of the 18 retained OCR snapshots | **18/18 passed**, identical fields and zero model calls; retained in `.local-data/refresh-benchmark/final-replay.json` |

The live walkthrough used this worktree's packaged application at loopback API/UI ports 8068/8038 and isolated PostgreSQL/EVM ports 55468/8568. It did not use the running application from a different checkout. Final model-schema changes were separately tested with actual local inference; the final-source replay checks that the measured deterministic cases remain identical.

Intermediate failures were retained and fixed: benchmark/build output sharing, Windows default text decoding, the initially unconstrained linker, the signed-status vocabulary mismatch, and a browser-test wait primitive incompatible with the application's CSP. CSP was not weakened. No failed check is counted as a pass.

## Reproduction and limits

Relevant entry points:

- `tools/make-ocr-benchmark.py` creates the original fictional PDFs.
- `tools/benchmark-frontend-extraction.py` compares frozen baseline classes with the current classes. It requires `.local-data/refresh.classpath` and the pre-change `.local-data/refresh-baseline-classes`. `--resume` validates frozen runtime identities; `--after-only` retains the same-byte baseline and archives intermediate results.
- `tools/replay-frontend-extraction.py` verifies final-source results against retained snapshots without OCR/model/network calls.
- `tools/test-frontend-intake.py` uses Edge and the offline frontend preview with controlled API replies.
- `tools/test-frontend-intake-live.py` exercises actual isolated loopback services with disposable fictional accounts.

Use the existing local Tesseract/data directory and pinned Python OCR environment via `FOLI_TESSERACT`, `FOLI_OCR_DATA_DIR`, `FOLI_LAYOUT_PYTHON` and `FOLI_LAYOUT_SCRIPT`. The benchmark accepts no private user-document directory. Raw outputs, screenshots and failed attempts stay under ignored `.local-data/refresh-*`; the saved report contains sanitized metrics only.

This is a demonstrated improvement, **not a universal perfect reader**. There were no independently labelled private user documents in this evaluation. Handwriting, arbitrary languages, novel tables, repeated ambiguous labels, damaged files and unsupported formats can still require manual entry. The app supports at most 64 confirmed facts per document. Missing/unreadable evidence and budget exhaustion remain visible instead of being filled with invented values.

For an existing draft, use **Read again locally**. Saved edits are retained and the latest suggestions appear separately. Previously confirmed facts, the original comparison baseline, wallet encryption, commitments and proof history are not rewritten. Issuer authority remains unverified unless established by a separate supported trust mechanism.
