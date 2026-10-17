# Foliolet PS32 — executed evidence register

This register distinguishes executed results, historical claims, failed tests, and untested scope. Dates are 16 October 2026; GitHub timestamps use UTC. The source baseline is `db55c2c6c1209e567713fa9ab08c5441bd55bc86`. All writes and disposable execution belong to `feature/ps32-final-winning-audit-20261016-1645`, never the original branch or runtime. Later acceptance evidence will be appended; this file is not an assertion that every pending feature passed.

## 1. Environment and source provenance

The container could not resolve GitHub. A real full source archive and Git bundle were created by a read-only GitHub Actions checkout, SHA-256 checked after download, and cloned into isolated local storage. Source recovery run: https://github.com/legoambarish/Foliolet/actions/runs/38935130981 . This was the actual repository, not an independent replacement laboratory. The earlier Library research archive was preserved; its independent experiments are not credited as current application tests.

Baseline environment: Ubuntu 24.04.5, Temurin Java 21.0.12, Python 3.13.16, Node 22.23.3, Tesseract 5.3.4. Full-stack jobs use PostgreSQL 17, Ganache, real Spring Boot/Web3j and Django, independent deployment trust pins, bundled Chromium, and local complementary OCR. Java application heap is 768 MiB; document benchmark readers use 512 MiB. Exact runtime inventories are retained in the associated artifacts. No private user records, existing chain, database, key or model store were used.

Artifacts expire after 14 days. This committed register and final reports are durable evidence summaries; reproduce using the committed workflows rather than treating expired artifacts as permanent storage.

## 2. Executed runs

| Run / source | Actual result | Evidence scope |
|---|---|---|
| [38934429615](https://github.com/legoambarish/Foliolet/actions/runs/38934429615), `d610a5e3d2e240c5f36d406503b9866ad4711b86` | 108 Java, 74 Django and 22 Node verifier tests passed; Solidity integration script passed; pip check passed | Original application source plus audit documentation/CI. Solidity assertion count is not invented. |
| [38935483259](https://github.com/legoambarish/Foliolet/actions/runs/38935483259), `f5b0ed977b9e0fdc09cb08541086c7249cd911ee` | Eight new source-association cases: **six failed**, two valid controls passed | Independent baseline reproduction, not a speculative finding. |
| [38938027342](https://github.com/legoambarish/Foliolet/actions/runs/38938027342), `2d5ca083370ba1ffe1c60b7dc468d16611aa2b4b` | 124 Java passed. Django discovered 83 tests; six new cases errored because the test helper `client()` collided with Django's client attribute | Actual test-harness defect, corrected without weakening production assertions. This run is not labelled entirely green. |
| [38938026869](https://github.com/legoambarish/Foliolet/actions/runs/38938026869), same source | Full-stack phases passed: 51 lifecycle checks, 23 security checks, five actual Chromium checks, 12 failure/restart checks, three CSV fallback checks, plus watcher/OCR-worker/QR suites | Real PostgreSQL, EVM, HTTP, browser, cryptography and filesystem execution. |
| [38940240171](https://github.com/legoambarish/Foliolet/actions/runs/38940240171), `25389eb7bb411ed6746235760a2645f1dcbfee97` | **128 Java tests, 96 Django tests, 22 Node verifier tests passed**, no Java failures/errors/skips; Solidity script passed | Includes source association, real vault filesystem security, real HTTP 307 non-forwarding, encrypted-session compatibility/migration, key retention, upload bounds and private-origin boundary. |
| [38941316476](https://github.com/legoambarish/Foliolet/actions/runs/38941316476), `0df9feb3767ece549c5d0c14f39885abb8259c00` | All earlier full-stack phases passed. New resilience script passed 15 checks, then failed because its final request used nonexistent `/wallet/` instead of `/` | The final session-continuity assertion must be rerun using the actual route. Do not label this run fully passed. |
| [38943212551](https://github.com/legoambarish/Foliolet/actions/runs/38943212551), `00e866b7001236a8fc241f9fee39cf0b8875315e` | **131 Java tests passed.** Django found 105 tests; one genuine-signed-PDF positive control errored in the new signature feature | Cloud default-deny tests passed. Signature inspection is not accepted until its positive cryptographic control passes; follow-up repair/validation is pending at this register revision. |

## 3. Independently reproduced source defects

`SourceAssociationRegressionTest` demonstrates six baseline failures: Candidate Name/ID falsely entering date handling; matching OCR elsewhere on a page falsely corroborating a field; different rotation frames falsely corroborating; a conflicting rendered label still earning corroborated provenance; off-page/overflowing geometry; and confidence outside the documented scale. Two controls verify legitimate date normalization and same-cell/label/value corroboration.

Production correction `dcfd3a5b1f2660d5b1fc4ec2ed698a3d4429bb6c` requires the same physical cell/frame, matching label and exact value, plus strong OCR. It rejects invalid geometry/confidence and fixes date-label classification. All eight cases subsequently passed. No Merkle, signature, credential, canonicalization or stored-key protocol was changed.

Eight `PrivateVaultSecurityTest` cases execute actual filesystem operations: key/ciphertext/backup retention over restart, strict IDs, symlinked files/parents/keys, POSIX owner-only modes, oversized ciphertext, and authenticated-encryption context/tamper rejection. These passed. This is not Windows ACL certification or protection from a compromised same-user/root process.

Ten wallet-transport tests include two actual disposable loopback HTTP servers: a 307 response cannot forward the private request body to the second server. Other checks cover numeric loopback, no environment proxies, no redirects, bounded response bodies, malformed origins, credential shape and explicit offline failure.

## 4. Comparable document benchmark — reproduced, not improved by this audit

Primary complete run: [38940026280](https://github.com/legoambarish/Foliolet/actions/runs/38940026280), evaluated source `18b7532a0549074136220bd6f654ce9b1c5ead48` against exact baseline `db55c2c6c1209e567713fa9ab08c5441bd55bc86`.

The same 14 fictional PDFs and 169 labelled facts were supplied to both revisions on the same runner. Both used the same complementary OCR worker source, local engines, absent LLM, 512 MiB reader heap and cold Java process per document. Source byte hashes were verified against the reader's reported hash. The Linux fixture font is explicitly selected DejaVu Sans; this is not a byte-identical reproduction of an earlier Windows/Arial corpus.

| Metric | Baseline | Repaired audit branch |
|---|---:|---:|
| Labelled facts | 169 | 169 |
| Emitted suggestions | 170 | 170 |
| Correct unique field/value matches | 168 | 168 |
| Recall, including review suggestions | 99.4083% | 99.4083% |
| Suggestion precision | 98.8235% | 98.8235% |
| Incorrect automatic suggestions | 0 | 0 |
| Incorrect review suggestions | 2 | 2 |
| Valid exact source fragments | 769/769 | 769/769 |
| Pipeline failures | 0 | 0 |
| Median wall time per document | 4.412 s | 4.346 s |
| Maximum wall time | 7.384 s | 7.404 s |
| Maximum sampled simultaneous process-tree RSS | 528,478,208 B | 520,626,176 B |

Recall is unique correct field/value pairs divided by labelled facts. Precision is correct emitted pairs divided by all emitted suggestions. Exact source-fragment correctness checks UTF-16 offsets and quoted bytes; it does not prove that a label belongs to a value or that the source is truthful.

This audit preserved the hotfix's accuracy while fixing adversarial gaps not represented by its original corpus. It did **not** establish an additional recall improvement. Timing differences are small, single-pass, and not a controlled causal speedup claim. RSS was sampled every 250 ms across the Java reader and children, not an exact continuous peak or total machine requirement. No real local model memory was included in this document comparison.

The historical 43.4-second/approximately-1-GiB observation used different conditions. These Linux measurements do not prove that the old hardware case has been repaired or reduced by a particular factor.

### Negative cases retained

`mixed-values.pdf` contains conflicting native Mathematics 91 versus rendered/OCR 71. The emitted native suggestion remains review-required with conflict and uncorroborated-rendering warnings; it is not automatically accepted. The ambiguous value is excluded from reliable ground truth, so it counts as an incorrect review suggestion.

`ocr-confusions-scan.pdf` contains the literal letter O in `9O`; OCR reads `90`. It remains review-required but is wrong against the original literal, producing one missed labelled fact and one incorrect review suggestion. High OCR confidence is not sufficient to resolve this ambiguity.

The first evaluation run [38939097756](https://github.com/legoambarish/Foliolet/actions/runs/38939097756) completed both synthetic passes but failed three public downloads with HTTP 500/502. The retried acquisition retained the exact preselected rows; no easier replacement samples were chosen.

## 5. Genuine public held-out documents — limitations exposed

Dataset: [CORD v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2), [original NAVER CLOVA project](https://github.com/clovaai/cord), CC BY 4.0. Original human annotations and source image hashes are retained. PDF conversion embeds original image bytes without resampling at an explicit 150-dpi page scale. No user private document is involved.

Frozen selection before Foliolet outputs: training rows 0 and 10 are calibration-only; test rows 0, 7, 14, 21, 28 and 35 form a six-document held-out stress set. These are Indonesian retail receipts, not Indian marksheets. They test out-of-domain generalization and safe review; they cannot establish academic credential accuracy.

All eight public receipts completed without a pipeline failure. Seven suggestions were emitted, all `REVIEW_REQUIRED`; there were **zero automatic suggestions**. All 16 emitted support fragments matched their source text exactly. Median wall time was 7.414 s, maximum 20.747 s; maximum sampled process-tree RSS was 507,756,544 bytes.

The runner intentionally leaves receipt precision/recall null because the academic extraction schema does not directly map to the dataset's full receipt annotation schema. A separate, narrowly defined manual check of the **grand-total field** uses original human annotations and visual inspection, not model output as ground truth:

| Dataset row | Split | Human-annotated total, normalized as an integer | Foliolet result | Assessment |
|---|---|---:|---|---|
| train 0 | Calibration | 114000 | No total suggestion | Safe abstention; not extraction success |
| train 10 | Calibration | 114000 | Decimal 25 | Incorrect label/value association; review required |
| test 0 | Held out | 60000 | Decimal 432901016 | Ticket/item identifier misassociated as total; review required |
| test 7 | Held out | 111000 | Decimal 111000 | Correct numeric total; review required |
| test 14 | Held out | 281435 | Decimal 281435 | Correct numeric total; review required |
| test 21 | Held out | 38000 | String `RP38.000` | Correct source literal, but unsupported currency normalization/type |
| test 28 | Held out | 380000 | Decimal 380000 | Correct numeric total; review required |
| test 35 | Held out | 54000 | Decimal 54000 | Correct numeric total; review required |

On the six held-out total targets, **4/6** are exact normalized decimal results, **5/6** identify the correct source total if the unnormalized `RP38.000` literal is included, and one incorrectly selects an identifier. All require human review. These are narrow target-field fractions on six examples, **not** general field-level precision or a statistically reliable performance estimate.

No extractor was tuned on these held-out outputs in this run. The findings argue against advertising universal invoice or real-world marksheet automation. Review requirements prevented automatic acceptance but did not make wrong suggestions correct.

## 6. Real end-to-end scope

The 51 lifecycle checks cover authenticated upload, fact confirmation, salted Merkle anchoring, genuine independent Node verification, nine tamper variants, hidden-field omission, concurrent single-use release, expiry, revocation, supersession, encrypted original/backup corruption and session-bound HTTP export. The 23 security checks include username race/database uniqueness, real Django login and confirmation, exclusion of suggestions from sessions, canonical proof rejection, trust pins and threshold-label protections.

The five Chromium checks perform native-table upload/review/confirmation/anchoring/selective sharing/independent browser verification; display 19 difficult scanned fields as review cards with zero automatically accepted facts; demonstrate server-side tracking of a 91-to-95 edit; and report no JavaScript errors or document requests beyond the allowed loopback services. These are actual browser actions, not screenshots substituted for functionality.

The twelve failure tests include genuinely absent OCR/model services and interrupted-job recovery. Some model metadata, prompt-injection response and delay cases use a local HTTP test double; they are not evidence of real oversized-model loading or real Ollama inference. Actual local-model tests are separately identified when available.

## 7. Real interruption observations

The later resilience run stopped the actual owned PostgreSQL container and actual EVM process, restarted the same stored state, then restarted the packaged backend. It verified fail-closed behavior during outages, preserved signing/vault keys, original ciphertext recovery, continuing proof validity and encrypted database-session envelopes. Measured database failure response: **30.012 s**; EVM outage response: **0.00749 s**; backend restart to network endpoint: **5.094 s**. These are single-run observations, not percentile service objectives.

The database connection wait motivated a configurable 5-second Hikari timeout. Its effect must be measured in the follow-up run. The final session-continuity test's incorrect URL was a test defect and must not be relabelled as a product failure or silently omitted.

## 8. Limits still requiring explicit qualification

Physical NFC/mobile behavior, actual Windows/macOS launch execution, a public Cloudflare tunnel, genuinely issuer-authenticated credentials, genuine Indian academic document accuracy, production multi-user load, and exhaustive malicious-PDF fuzzing are not established by these results. No security audit proves that all possible bugs have been found. Existing dependency advisories remain a separate risk even when regression tests pass.
