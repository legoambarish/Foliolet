# OCR and fact extraction repair

This change is local to `feature/digilocker-assisted-intake`, starting at `6db30e1520211b0dae88c8b47200a9ed1b6089c7`. It preserves Spring/Django/PostgreSQL, the encrypted vault, the existing EVM commitment and disclosure flow, the watcher and local Ollama. Main and cf are not changed. No follow-up push is part of this repair.

## Root causes and fixes

| Observed cause | Implemented correction |
| --- | --- |
| Only colon/equal-delimited lines reached the model; tables and adjacent/vertical fields had no candidates. | `LayoutFacts` constructs rows/cells from positioned PDFBox/OCR words. It associates explicit fields, adjacent cells, labels above values, and subject rows with specific printed column headers. Centered plural subject headings and a printed maximum note are supported. “Total marks” retains that meaning rather than being renamed to an inferred assessment type. |
| Any column warning rejected all facts on that page. | Column warnings remain visible. Each field is validated using its own label, value and header fragments. Unrelated noise and layout warnings cannot reject a different, well located field. |
| Native words had no positions; OCR/source offsets could refer to different text. | `PositionedTextStripper` captures PDFBox's actual writer offsets, sorted glyph positions and visibility. Every fragment must equal the exact substring at its offsets. Each OCR pass has an independent coordinate frame, rotation, method and shifted offsets. Python offsets are emitted as UTF-16 offsets for Java. |
| Mixed pages required whole-line agreement or lost sparse embedded text/image-only fields. | Both readings remain in the page snapshot. Reconciliation is per field; contradictions and alternative readings remain reviewable. A required rendered-page check that fails cannot silently promote native text. |
| A page average hid weak field values; confident wrong digits could pass. | Label/value/header confidence is evaluated at field level. Very weak values are withheld; unrelated weak words do not veto other fields. **All OCR-only suggestions require visual review**, including confident readings. Characters are never guessed or repaired. |
| Overprinted PDF digits could concatenate into a false number; invisible text could look legitimate. | Visibility and glyph overlap are tracked. Hidden text is excluded from layout candidates. Fields affected by overlapping glyphs are withheld, including concatenations that parse as strings; unaffected fields survive. Nearby unmapped/hidden glyphs require review. |
| Low resolution and one segmentation mode failed on scans, tiny print and security backgrounds. | Bounded rendering up to 300 dpi/8 million pixels, complementary Tesseract page/block readings, rotation before contrast processing, and bounded contrast/threshold readings. All original readings retain separate provenance. |
| A few confident garbage tokens could win orientation selection. | Select using credible character coverage as well as confidence. Process orientation before spending the budget on contrast variants. Both quarter-turn and upside-down scans are benchmarked. |
| Tesseract still failed on the actual low-quality marksheet. | A compact CPU RapidOCR fallback runs only after weak Tesseract readings. Its three bundled ONNX weights total **31,749,509 bytes**. Exact package versions and each model hash are checked before inference. Networking is denied, ONNX telemetry disabled, CPU threads bounded, inputs bounded and the child is killable. Missing/tampered fallback packages preserve Tesseract/manual entry. |
| OCR merged printed labels with values, or included unrelated bilingual text in the label. | Exact known label prefixes can locate a value in a merged cell, with a boundary-review reason. An exact printed English DOB anchor can be isolated from neighbouring script without inventing a translation. Unrecognized OCR delimiter labels are withheld with a distinct diagnostic. |
| Model proposals could invent values or be discarded without a useful reason. | Structured layouts are processed deterministically. For otherwise unassociated cells, local Qwen may select existing cell IDs only. Server code supplies all literal values. Unknown IDs, other chunks, different pages/layers and non-adjacent pairs are rejected. Model-selected associations require review. Calls/chunks/context and the total linking deadline are bounded. Model failure does not remove deterministic fields. |
| Indicators reopened and OCRed pages again, consuming an independent budget. | Reuse positioned readings for logo checks where available. Extraction and indicator inspection share an overall child deadline. QR and logo coverage are separate, so a working QR check does not imply a successful logo check. QR contents are hashed/classified locally and never followed. |
| Many failures became the same “No verifiable fields” message. | Reports retain words, aligned words, rows, cells, candidates, groups, support/review counts, page counts, named rejection reasons, model calls/status and latency. The UI shows human-readable reading details and distinguishes missing associations, rejected candidates and unavailable linking. |
| Uncertain fields could be placed directly into confirmation rows. | Supported fields populate editable rows. Uncertain fields appear under **Check before using**, with reasons, alternative readings and original-page access. **Use after checking** explicitly adds a field. The server-rendered fallback also excludes uncertain fields from automatic rows. Text is rendered with escaping/textContent. |
| “AI unchanged” was misleading for deterministic suggestions. | UI copy describes the saved proposal and edits without attributing every field to AI. The immutable server baseline, canonical comparison, source hash/version and added/edited/removed tracking remain authoritative. Late reading after confirmation cannot create a baseline retroactively. |

`FactSuggestions.parse` remains a conservative compatibility parser for old v1 proposals/tests. New intake calls `LayoutFacts`; the former whole-page rejection path is not used for new suggestions. Full-document Foli retrieval/chat/review and exact citation validation remain separate from fact suggestions.

## Meaning of the three outcomes

* **Source-supported:** a deterministically located association has exact retained source fragments and no outstanding field issue. This establishes what the retained source says; it does not establish document authenticity or truth.
* **Needs review:** an image transcription, conflicting reading, model-selected association, ambiguous date, unclear label/value boundary or other named field issue. These values are not automatically accepted into fact rows.
* **Cannot safely extract:** missing/unaligned evidence, hidden/overprinted numeric content, very weak OCR, unknown labels, unsafe CGPA, collisions or exhausted limits. The reason is retained; original files and manual entry remain available.

Holder confirmation creates holder assertions. Watcher continuity, a possible DigiLocker graphic/QR, extraction lineage and issuer verification remain different concepts. **No issuer signature is validated by these heuristics.**

## Reproducible benchmark

The machine-readable results are in [ocr-p0-benchmark.json](verification/ocr-p0-benchmark.json). The companion [verification record](verification/ocr-p0-tests.json) records actual checks. Do not substitute historical test totals from previous feature work.

The corpus consists of 14 clearly fictional PDFs with **169 explicit golden fields** and two private PDFs already present in this worktree's encrypted vault. Both private originals were copied locally for benchmarking; no existing records were retried, modified or confirmed. Their values/transcriptions, model output, credentials and benchmark intermediate files remain ignored under `.local-data/ocr-p0`.

Fictional layouts include a five-subject marksheet with separate maximum/obtained/grade columns, adjacent and stacked labels, two-column layouts, PDF form widgets, image-only/blurred scans, 90/180 degree rotations, 5.5 pt text, image/native contradictions, invisible text, overprinted marks and letter/digit confusions. These go beyond the original `Math: 90` fixture. The golden target for literal `9O` is the string `9O`; recognizing it as numeric `90` is scored as a false suggestion, even when confidence is high.

Before/after use identical PDF bytes. Pre-fix compiled classes were frozen before production changes, using the same reader adapter and local services. Per-document SHA-256 is included in the report. Recall requires both the correct path/association and the entire canonical value. Precision counts *all emitted suggestions*, with automatic and review results separately reported. Fields deliberately made ambiguous have no unambiguous target: an emitted guess is counted as false even if marked for review. V1 fields are classified in the automatic column because that UI automatically populated them; v1 did not have the new support enum.

Latency is observed wall time, not a service SLA. RSS is a 250 ms sampled peak of the benchmark JVM, reader JVM and OCR child processes together; it excludes the separately resident Ollama process. It is not a hard OS memory quota. Loading the optional OCR engine costs additional RAM. The reader retains its 512 MiB Java heap ceiling, bounded pixels/text and process deadline. Very long image-only documents can still reach the overall reading budget; omitted coverage must remain explicit.

The two private PDFs have **no independently human-labelled golden values**. We report candidate counts, field classes, exact source binding, latency and memory, not invented real-document recall/precision. Their extracted values still require human checking. Authentic DigiLocker login/download, issuer cryptography and physical NFC remain unverified.

### Measured results

These figures describe this corpus, not a claim of universal document accuracy. Recall includes suggestions that require explicit review.

| Metric | Before | After |
| --- | ---: | ---: |
| Correct complete facts / 169 labelled targets | 4 | 168 |
| Recall, including review suggestions | 2.37% | 99.41% |
| Precision across every emitted suggestion | 80.00% (4/5) | 98.82% (168/170) |
| Exact-value accuracy on emitted paths with a golden target | 100% (4/4) | 99.41% (168/169) |
| Automatically populated suggestions: correct / total | 4/5 | 63/63 |
| Incorrect automatically populated suggestions | 1 | 0 |
| Review suggestions: correct / total | 0/0 | 105/107 |
| Median total latency, all 16 documents | 3,321.5 ms | 3,265.5 ms |
| Maximum total latency, all 16 documents | 32,628 ms | 43,449 ms |
| Maximum sampled simultaneous reader/OCR RSS | 512.79 MiB | 1,016.77 MiB |

The baseline's 100% exact-value figure covers only four emitted paths with known truth; it hides the severe recall failure and the invisible-text false suggestion. It is not evidence of a better baseline. The after run has two false **review** suggestions: native text contradicting the rendered mark, and a scanned literal `9O` read as `90`. Both are explicitly excluded from automatic confirmation rows. Overprinted fields and their string-concatenation variants are withheld. No incorrect automatic suggestion was observed in this labelled corpus.

On the two private failed scans, proposals increased from **0 to 1** and **0 to 11**, all requiring review. The recovered classes include an identity DOB and marksheet identity/subject fields. The marksheet's Mathematics total was withheld because of a column collision. Counts measure surfaced proposals, not validated private-document accuracy. The slower private scan took 43.449 seconds. More difficult OCR uses more memory; the improvement does not come with a memory reduction.

### Executed test matrix

| Check | Actual result | Coverage |
| --- | --- | --- |
| Java unit suite and Boot packaging | 108 passed; no failures/errors/skips; package built | Positioned extraction, layout, dates/IDs, ambiguity, hidden/overprinted glyphs, source offsets, confidence, lineage races, access controls, existing Foli and wallet behavior |
| Java live integration | 7 passed; no failures/errors/skips | Actual Tesseract, local Qwen with external Java networking denied, supplied wordmark at several sizes/rotation; provisional indicators only |
| Django dashboard | 74 passed | Role/proxy/UI regression and server-rendered uncertain-field exclusion |
| Watcher unit / PowerShell companion | 11 / 3 passed | Recursive downloads, partial files, tampering, pairing expiry and managed stop |
| Node proof/security/UI/QR | 23 passed | Independent proof and malformed/forged input handling; actual three test files listed in the verification record |
| Contract gate | Passed | Authorization, immutable commitments, unsupported assurance, supersession, revocation and seven Merkle shapes |
| Offline compact OCR boundaries | 4 passed | Network denial, pinned versions and bundled model hashes, tampered weights |
| Live intake/Foli/disclosure | 46 passed | Actual private runtime, watcher provenance/hash changes, forged logos/QRs, fact edits, issuer distinctions, original Foli chat/review, Merkle disclosure and lifecycle |
| Failure injection | 12 passed | Refused/missing/oversized/cloud model, forged cell IDs, timeouts, absent OCR, interrupted backend/retry, oversized uploads |
| Existing Edge intake UI | 11 passed | Upload, theme/mobile layout, source access, edits, unchanged proposal, original disclosure UI |
| New realistic marksheet Edge walkthrough | 5 passed | 19 supported native facts; original preview; confirm/anchor/single-fact independent proof; 19 scanned review cards; explicit acceptance and modified-value tracking; no off-loopback requests |
| CSV fallback / packaged JAR reader | 3 / 1 passed | No guessed CSV facts; manual confirmation; real packaged reader returns exact source |
| Native desktop / concurrent status IO | 8 / 1 passed | Cold/warm single-action launch, duplicate/foreign-port refusal, retained data; one concurrent status test with 101 updates |
| Same-byte benchmark | All 16 completed in each phase | 14 fictional layouts with golden values and two private scans without golden values |
| Retained state and branch checks | Passed | 102 pre-existing encrypted originals/keys/pins unchanged; existing Evidentia files and main/cf refs retained |

Failed intermediate runs were retained locally: an overlapping-digit candidate also bypassed the first fix as a string, prompting the final type-independent rejection and regression test; OCR mocks needed the new layout contract; a Mockito restub needed `doAnswer`; an active Windows JAR required managed stop before packaging; the browser source selector needed disambiguation and bounded retry for the existing 429 gate; the first desktop invocation overlapped an already-held startup mutex. Each applicable check was rerun successfully. The two false review suggestions above remain measured limitations. Ganache used its JavaScript fallback after a native module mismatch. The live networking test emits Java 17's SecurityManager deprecation warning.

Live intake/failure/existing-UI suites preceded the last focused layout refinements. The final 108-unit build, 16-document benchmark, new full browser walkthrough, CSV/packaged-reader and desktop checks cover the resulting code. The historical 80-question Foli campaign was not rerun; the current Java suite did pass its 60/60 source-page and 40/40 fine-print retrieval assertions. Remote CI, Docker, production deployment, authentic issuer verification and physical NFC were not tested.

## Exact Windows setup and launch

Use Windows PowerShell 5.1, Java 17, Python 3.12, Node.js and Git. The tested checkout is `C:\Users\User\Downloads\Foliolet-digilocker-intake`. The portable PostgreSQL/Tesseract runtime may be in this checkout or the retained sibling `C:\Users\User\Downloads\Foliolet-testcloudflare`; existing databases, models and keys must not be reset.

```powershell
Set-Location -LiteralPath 'C:\Users\User\Downloads\Foliolet-digilocker-intake'
.\.venv\Scripts\python.exe -m pip install -r django-service/requirements.txt -r tools/requirements-dev.txt -r tools/requirements-ocr.txt
.\.venv\Scripts\python.exe -I tools/ocr-layout-worker.py --check
```

Expected integrity check: `ready: true`, `modelBytes: 31749509`. The fallback models are bundled in the pinned RapidOCR wheel; inference must not fetch any weights. Code/package and weight licensing are documented separately by the [maintainer](https://rapidai.github.io/RapidOCRDocs/main/en/model_licenses/); the implementation uses its small CPU ONNX models rather than a vision language model. Package installation needs a network connection once; document inference is local.

**Normal launch:** double-click the existing `Foliolet` desktop shortcut or `Foliolet.vbs` in this checkout. It opens the native launcher, checks/install project dependencies (including the pinned compact OCR runtime), builds stale Java source, starts the saved local database/EVM/model/backend/UI, verifies readiness and opens `http://127.0.0.1:8008/`. Its normal workflow needs no terminal, JSON, certificate or field path. The first build/model warmup can take a few minutes. Repeated clicks reuse the ready instance. Stop uses the existing managed shutdown and preserves state.

The equivalent diagnostic command is:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File .\tools\launch-foliolet.ps1
```

Logs are local under `.local-data/desktop-*.log`; opening them may expose private diagnostic state. `start-foliolet.ps1 -CheckOnly` checks readiness. The private ports are PostgreSQL **55438**, EVM **8548**, Spring **8088**, Django **8008**, and managed Ollama **11444**. Existing unrelated services are not reused or stopped. No public tunnel is started.

## Demonstration

1. Start Foliolet and sign in as a disposable holder. Use **Upload and review facts** to upload `.local-data\ocr-p0\fixtures\native-table.pdf` as Education. This is explicitly fictional test data.
2. Wait for the 19 fields. Open **Source evidence** for Mathematics, check the printed header/row and **View original page**. Name, enrollment, DOB, CGPA, five marks, five maxima and five grades are independently located. Normal users never edit field paths.
3. Keep the reviewed rows, tick confirmation and press **Confirm facts**. The server records the saved proposal as unchanged. Press **Anchor commitment** explicitly.
4. Press **Share a proof**, select only Mathematics marks, fill recipient/purpose and create the local proof link. Open it in a recipient tab and press **Open disclosed facts**. Only the selected fact is released; the original and other values remain private. **Check proof and chain** runs the existing independent browser check.
5. Upload `scan-table.pdf`. Its 19 fields appear under **Check before using**, with empty automatic fact rows. Open the original, then press **Use after checking** on Mathematics. Change 91 to 95 and confirm: the server must record an edit; this does not claim the edited mark is source-supported or issuer-verified.
6. Try `ambiguous-table.pdf`, `mixed-values.pdf`, `native-hidden.pdf` and `ocr-confusions-scan.pdf`. Overprinted numbers are withheld, native/image disagreements remain reviewable, hidden text is excluded, and a confident `9O`/`90` confusion remains a known reason to inspect the image.

The automated browser demonstration is `node tools/test-ocr-intake-ui.cjs`. It saves screenshots and a result record under `.local-data/ocr-p0/walkthrough`. Screenshots contain fictional documents only. For initial fixture generation, use `python tools/make-ocr-benchmark.py` with the development PDF dependencies; do not regenerate between before/after runs because PDF bytes can change.

## Remaining limits

OCR certainty is not factual certainty. The local OCR engines can agree on a wrong digit, especially letter O/zero, security backgrounds, handwriting or poor source resolution. Review is mandatory for image-derived fields. Multi-level/merged tables, arbitrary scripts, complex text directions and unrecognized labels may still need manual entry. No missing marks or CGPA is calculated. General two-column CSV still uses its existing manual fallback. This is a bounded extractor, not a universal certificate schema or issuer verifier.

Private real-document precision remains unmeasured without independent labels. A successful fictional browser/chain demonstration must not be presented as an authentic DigiLocker issuance or an actual government verification.
