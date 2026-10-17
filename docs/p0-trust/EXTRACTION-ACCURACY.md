# Intake extraction follow-up — 17 October 2026

The reported cards were produced by deterministic label/table matching, before any model call. The fix is limited to intake extraction, its source-linking prompt, intake presentation and regression/benchmark tooling. Wallet cryptography, proof formats, disclosure and sharing logic are unchanged.

## Corrected behavior

- A separately positioned colon is a separator, not a person's name.
- Printed English anchors such as RESULT and Mother's Name are isolated from legacy-font prefix noise, with their exact source spans retained. Date-of-result labels remain dates.
- Headers, subject lists and prose cannot become result/name values. TOTAL is not paired with TOTAL (IN WORDS).
- Split SUBJECT/CODE and POSITIONAL/GRADE captions, theory/practical/total columns, percentage marks followed by words, and wrapped subject names are handled separately. Assessment section titles are not appended to the previous subject.
- The local model fallback prompt explicitly excludes headers, punctuation, subject lists and conflicting readings. It still selects existing source cells; it cannot supply new values.
- A completed reread displays the latest proposal without replacing the immutable original comparison baseline or unsaved holder edits. Preview comparisons continue to use the original baseline. Server-side lineage remains authoritative.
- The extraction version is `intake-facts-3-labels-tables`. Historical baselines are not rewritten.

## Actual local samples

All three PDFs in the supplied intake folder were read locally, including the rendered pages of both marksheets. Private source text, files, images and field values were not sent to Google or committed. The final extractor was also replayed against the exact retained pre-change reader snapshots, eliminating OCR run-to-run variation from the comparison.

| Sample | Before suggestions | After suggestions | Source-supported | Still require review | Model calls |
|---|---:|---:|---:|---:|---:|
| Education A | 11 | 21 | 16 | 5 | 0 |
| Education B, reported screenshot | 6 | 29 | 24 | 5 | 0 |
| Identity document | 11 | 11 | 0 | 11 | 0 |

These counts measure coverage, not universal accuracy. Twenty-eight targeted assertions passed: five numeric marks in the first marksheet, fifteen theory/practical/total marks in the second, the separator/name defect, the screenshot's date/mother/result associations, rejection of bogus fields, wrapped subject preservation, following-row retention and zero model calls. All **61/61** emitted citations and label/value/header fragments matched exact source offsets (UTF-8 JSON, Java UTF-16 offsets).

The screenshot's correctly printed date, result and mother's name now have corroborating native/OCR readings. Review warnings remain where readings disagree, including the identity sample. Source corroboration is not issuer authentication. This is not a complete gold-standard evaluation of every possible field; unusual layouts, fonts, names, outcome vocabulary and ambiguous dates can still require manual entry/review.

## Bounded model screen

One model-list request identified 16 distinct candidate text/document models for screening. Moving aliases, the duplicate Flash-Lite preview, custom-tool variants and specialist image/audio/music/research/robotics/computer-use endpoints were excluded. Eight independently fictional cell-layout cases covered the reported failure patterns, table columns, dates, leading zeros, OCR confusion, contradictory readings and document prompt injection. Each model received the same batched cases and strict prompt with a maximum 1,800 output tokens. No private sample content was pseudonymized or sent to cloud.

This provider-only evaluation emits literal facts with source IDs. The production fallback retains its stricter existing-cell-pair schema and validation; these scores are not end-to-end product accuracy.

| Model | Exact cases / 8 | Correct facts / 11 | Extra/wrong facts | One-call duration | Outcome |
|---|---:|---:|---:|---:|---|
| Gemini 3.1 Flash Lite | 8 | 11 | 0 | 2.000 s | Complete |
| Gemini 3.5 Flash Lite | 8 | 11 | 0 | 1.875 s | Complete |
| Gemini 3.7 Flash | 8 | 11 | 0 | 10.079 s | Complete |
| Gemini 3.8 Flash | 8 | 11 | 0 | 17.171 s | Complete |
| Local Qwen 3 4B Instruct | 5 | 8 | 2 | 33.046 s | Complete |
| Gemini 3 Flash preview | — | — | — | 7.313 s | Output cap; unusable JSON |
| Gemini 3.5 Flash | — | — | — | 8.984 s | Output cap; unusable JSON |
| Gemini 3.6 Flash | — | — | — | 8.656 s | Output cap; unusable JSON |
| Gemini 2.5 Flash Lite / Flash | — | — | — | — | Each returned HTTP 404 |
| Gemini Omni 1.1 Flash | — | — | — | — | HTTP 429; stopped entire screen |

Limits: at most 18 generation attempts and 60,000 conservatively accounted tokens, serial calls, 10-second pacing, bounded responses, no retries, no tool calls/uploads, and an existing-ledger replay guard. The run stopped after **10 generation attempts**, immediately on its first 429. Successful responses reported **16,948 tokens**; conservative accounting including unknown failed-request usage was 31,870. Project-wide remaining quota/balance is not visible from these calls; this is not a claim that no quota was reached.

Omni Flash preview, 2.5 Pro, 3.1 Pro preview, 4 Argon and both Gemma 4 candidates remain **untested** because of that stop. Planned prompt ablations were also skipped. A single small text-cell screen cannot establish the best model across real PDFs or statistically distinguish the two Flash Lite timings. The existing 3.5 Flash Lite setting remains appropriate; there is no evidence here to justify switching it to 3.1. Both were perfect on this limited screen. The application intake fixes require neither cloud calls nor a model switch.

The replacement key was used only through an ephemeral environment variable, was not written to configuration/Git, and was not printed by the benchmark. Actual paid-account terms remain unconfirmed, so the application cloud privacy gates were retained. See Google's [3.1 Flash Lite model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), and [data-use terms](https://ai.google.dev/gemini-api/terms). Local evidence and sanitized metrics are distinguished in `EXTRACTION-METRICS.json`.

## Validation and use

The full Java package run completed **148 tests, zero failures/errors, four platform skips**. Django's intake suite completed **11/11** tests. Real Edge browser checks passed **13/13**, including upload/review, source-page access, reread refresh, preservation of unsaved edits and the original baseline, confirmation/lineage, CSRF and mobile light/dark layouts. The repeated-reread test exposed and verified the fix for an existing async event-handler bug that left the button disabled. JavaScript syntax and offline benchmark scoring checks passed.

The isolated private application runs at `http://localhost:8018/`. For an existing draft, choose **Read again locally** to obtain the current extraction. If the form has unsaved edits, those remain untouched; save or deliberately discard them before expecting autofill replacement. Confirmed records and historical baselines are not silently reprocessed. No public deployment or change to main is included.
