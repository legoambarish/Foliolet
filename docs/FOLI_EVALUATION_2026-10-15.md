# Foli evaluation — 15 October 2026

These are executed results from the existing Windows `cf` checkout, not proposed targets. All evaluation documents/accounts are newly generated synthetic fixtures. The corpus is authored and keyword-rich; it is not an independent sample of real legal contracts. Source alignment, passage recall and legal correctness are distinct measurements.

## Release gates

| Gate | Measured result |
| --- | --- |
| Java, including real child readers, real OCR and live loopback inference | 72 tests; zero failures, errors or skips |
| Django, including receiver separation and CSRF | 63 passed |
| Separate Node proof verifier/UI | 22 passed |
| Solidity registry | PASS on real in-process Ganache, including seven Merkle-tree shapes |
| Existing live wallet workflow / security | 51 / 23 real HTTP, PostgreSQL, EVM checks passed |
| Live Foli source/security reading | 26 checks passed |
| Live Foli adversarial/DB/chain/log gate | 19 checks passed; authoritative row counts and chain block unchanged |
| Real Edge 155.0.4283.45 / Playwright UI | 18 browser checks plus fixture setup passed, zero JavaScript exceptions or external requests |
| Packaged Spring Boot JAR reader | PASS with actual PropertiesLauncher and exact synthetic text |

Authorization coverage includes two holders, OFFICER and ADMIN, wallet-owner enforcement even against ADMIN, legacy uploader/admin access, stale hashes, AES-GCM tampering, replacement/deletion, role changes, job ownership and no restore/write behavior. The bounded child-reader tests include 125-page extraction, original rendering, corrupt input, cancellation, a blocked output consumer/time budget and scratch cleanup. Malicious PDF tests cover opening JavaScript, hostile metadata, oversized image dimensions and recursive forms. New UI state faults are explicitly synthetic responses; real read/chat/review/OCR/cancel flows use the live services.

## Eighty-case application benchmark

The fixed corpus contains 40 explain-quoted-clause prompts, 20 independently phrased questions, 10 deliberately unavailable facts, 5 write requests and 5 general questions. A document pass requires the expected gold page and complete expected passage in a verified citation (whitespace normalized only for the gold comparison); a valid alternate passage can therefore be a strict rubric miss. This is evidence-location support, not a blinded judgment of every answer sentence.

Final result: **78/80 (97.5%) rubric passes**. The complete raw answers and source metadata are in `.local-data/foli/phase-5-qa-release.json`.

| Kind | Passes / cases |
| --- | --- |
| document | 58/60 |
| unanswerable | 10/10 |
| write | 5/5 |
| general | 5/5 |

**66 returned chat citations were reopened and checked against exact current source offsets; zero quotation-alignment failures.** This does not mean every attached excerpt semantically supports every statement.
Observed app-job latency median 1.494 s, maximum 26.010 s. These include queue contention from concurrent browser/review tests; ten starts/minute is respected with explicit waits. Use the isolated raw-model timings below for inference comparisons.

Strict misses (retained rather than relabeled as successes):

- **P05** — expected page 13; cited pages none; NO_SOURCE_SUPPORT. Response excerpt: The amount of compensation you can recover is capped at the fees paid in the previous month, as stated in Clause 5. However, this cap does not apply to personal injury caused by negligence, which is exempt from the financial liability limit [source reference omitted]. Additionally, consequential damages are excluded under Clause 29, meaning they are not recoverable even if they arise from a proven defect. The 100-unit limit applies to aggregate usage across linked accounts, as defined in Clause 33, but this relates...
- **P13** — expected page 37; cited pages 100; INTERPRETATION. Response excerpt: No, an email is not enough to cancel, as the footnote to Schedule C states that email notice alone is not sufficient for cancellation. [E2]

Earlier retained runs include 74/80 before abstention/inline-ID handling, 75/80 with that hardening, an interrupted refinement exposing sparse excerpt-ID/clause confusion, and the targeted local-ID regression. The final implementation suppresses common boilerplate, prioritizes requested headings and uses compact IDs for each chat answer. The early completed-job capacity bug and incorrect portable OCR data path were fixed; their failed logs were preserved. No partial run is counted as 80 completed cases.

## Whole-document fine-print gate

The actual 125-page PDF review completed in **19.866 s**, finding **40/40 authored critical passages** and **40 exact source quotes**, including the overriding page-125 exception. The earlier measured pass was 18.171 s.

Coverage: `{"checklistPages": 125, "definitionPassages": 3, "failedBatches": 0, "mode": "whole-document", "semanticChunks": 125, "semanticComplete": true, "totalChunks": 125, "totalPages": 125, "unreadablePages": 0, "unresolvedReferences": 1}`.

Flagged-page precision versus the authored clause-page set: **100%**. This metric concerns passage locations, not correctness of generated legal interpretation. Three definition passages and one unresolved schedule reference remain explicit. Tiny-print extraction uncertainty is retained. Twelve broad checklist categories supplement source-ordered semantic mapping; unreadable/limited pages cannot support an absence claim.

## Reader and OCR measurements

| Fixture | Elapsed incl. enrollment / read | Status | OCR character / word error |
| --- | --- | --- | --- |
| scan.pdf | 2.334 s | OCR | 0.0% / 0.0% |
| rotated.pdf | 2.752 s | OCR | 0.0% / 0.0% |
| mixed.pdf | 2.528 s | MIXED_OCR | not scored |
| two-columns.pdf | 1.156 s | TEXT | not scored |
| unreadable.pdf | 2.842 s | UNREADABLE | not scored |
| plain.txt | 0.860 s | TEXT | not scored |
| table.csv | 0.907 s | TEXT | not scored |

Every fixture page was accounted for. OCR gold comparison normalizes whitespace only; the two clean printed scans recovered negation and INR 9300 exactly. This small sample establishes neither handwriting accuracy nor performance on low-resolution or multilingual legal scans. Mixed sources retain both native and OCR readings when they differ. Multi-column text warns about visual reading order; blank pages stay unreadable. Reader identity: foli-pages-2.

## Actual model comparison

Same machine, Ollama 0.40.3, Q4_K_M, 8192 context, temperature 0.1, seed 42, one generation, 350-token comparison ceiling, ten synthetic raw-model tasks. These tasks are separate from the 80 application cases and do not apply the application write/citation guards. Cold means unloaded model, not a reboot or purged OS disk cache. Warm median uses the remaining nine heterogeneous short prompts. Model VRAM is from `/api/ps`; GPU usage includes desktop/driver allocations. RAM is the measured native llama-server process working set, not total application memory.

| Model | Package bytes | Raw tasks | Cold s | Warm median s | Warm median tokens/s | Model VRAM GiB | Native runner RAM GiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| qwen3:4b-instruct | 2,497,293,803 | 8/10 | 4.628 | 0.347 | 81.58 | 3.607 | 0.718 |
| gemma3:4b | 3,350,272,403 | 8/10 | 6.101 | 0.407 | 76.80 | 2.822 | 0.971 |
| qwen2.5:7b | 4,683,087,332 | 7/10 | 6.477 | 0.612 | 51.83 | 4.645 | 0.666 |
| qwen2.5:3b | 1,929,912,432 | 1/10 | 4.316 | 0.556 | 101.30 | 2.238 | 0.671 |

Actual **CPU-only Qwen3 4B**: 6.743 s for 26 generated tokens, 14.34 tokens/s, 4096 context, model VRAM **0 bytes**, native runner RAM 2.951 GiB. This measures CPU generation, not a forced full-GPU OOM experiment.

**Selected: qwen3:4b-instruct**, the smallest compared candidate meeting the retained application/fine-print gates with a permissive Apache-2.0 license. The 3B package is smaller but scored 1/10: malformed evidence IDs/arrays, failure to preserve source support and a false claim that a requested edit was completed. The application never exposes write tools. Gemma ties 8/10 at a larger package size under its separate terms; 7B scored 7/10 and was slower.

Raw-model limitations remain: both 4B candidates failed the conflict task; Qwen safely abstained on the injected notice passage, and Gemma missed the linked-account definition. A larger package did not remove these weaknesses. Exact digests, quantization, full model-specific license receipts, responses, RAM/GPU snapshots and CPU configuration are retained in `.local-data/foli/model-benchmarks-selected.json`.

## Privacy, offline scope and limits

All application listeners are numeric loopback. Ollama `/api/status` reports cloud disabled from environment; the native llama-server was also observed with `--offline` and `--no-webui`. Java live inference passed with non-loopback connects denied, with a negative external-socket control. The browser test permits only local requests. The live injection canary was absent from the private Java/Django logs, and authoritative DB counts/chain height were unchanged during the Foli-only adversarial gate.

**Not performed:** physical Windows network-adapter disconnection; OS-level egress sandboxing of every native process; exhaustive native-parser security review; real-world multilingual/handwriting accuracy or legal-interpretation validation. The reader heap/wall-clock boundary limits resource failures, not host-user privileges. Normal source citations can still attach an imperfect interpretation, and safe abstentions can miss answerable questions. The source viewer, scope warnings and full-document mode remain essential.

No receiver routes/assets, blockchain contracts, share authorization, document mutation or Cloudflare configuration were changed for Foli. New runtime state is local-only. The checked-in source contains no model weights, secrets, production customer documents or paid services. See [startup and architecture](FOLI_IMPLEMENTATION.md) and [demonstration](FOLI_DEMO.md).

## Actual runtime outage and recovery

The specifically verified local Ollama process and its own runner were stopped after the corpus finished. Health became OFFLINE; a real general-chat job returned ERROR/OFFLINE in 0.067 s with no answer or fallback. The documented launcher restarted the same runtime/models; health returned READY and a real inference job completed in 3.791 s. PostgreSQL, Spring, Django and chain state were preserved. Receipt: `.local-data/foli/phase-5-outage.json`.

## Application workload memory

After restarting Ollama, another actual 125-page full review completed in 22.763 s. Across 23 OS samples, native runner peak working set was **2.328 GiB**; lowest observed system free RAM was **10.421 GiB**. This is a workload observation, not a hard process-memory ceiling.
An earlier extended mixed CPU/GPU/model/application session reached a native runner working set of **8.493 GiB**. Its cause was not isolated; it is retained as a capacity limitation rather than erased by the fresh-runtime result. The short comparison table above must not be interpreted as a long-duration RAM guarantee. Receipt: `.local-data/foli/phase-5-app-resources.json`.
