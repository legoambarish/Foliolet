# Assisted-intake verification record

## Current-folder list regression, 17 October 2026

Verified locally in `C:\Users\User\Downloads\Foliolet` on the PS32 feature branch. These results are separate from the historical rehearsal below.

| Gate | Result | Local evidence |
| --- | --- | --- |
| Intake service workflow | 13 tests passed | `.local-data/tracked-files-java-tests.log` |
| Private inventory/import plus existing intake proxy | 17 tests passed | `.local-data/tracked-files-django-tests.log` |
| Shared Windows stable-file reader and companion | 13 tests passed | `.local-data/tracked-files-companion-tests.log` |

The regressions cover current-holder/current-pairing isolation, stale file versions, tampered selections, deleted files, exact selected bytes, receipt reuse, absence from the public receiver, CSRF and loopback access. Manually selecting an existing file does not imply a connected watcher or inherit an old agent observation.

Live browser checks used a separate synthetic holder and folder: arrival appeared first without reloading; selecting the middle CSV saved its exact bytes (SHA-256 checked against its encrypted-vault download); the real companion imported a TXT and selecting that row opened the same saved credential. The list fit at 1280px and 390px in light and dark themes, with no browser errors. Captures are retained in `.local-data/tracked-files-test/`. The user's existing Enroll tab was refreshed only after confirming it had no pending file/name input; its live folder status and current-folder list were present after restart.

To repeat the focused tests without overwriting a running backend JAR:

```powershell
.\spring-boot-service\mvnw.cmd -f spring-boot-service/pom.xml -B '-Dtest=IntakeWorkflowTest' test
.\.venv\Scripts\python.exe django-service/manage.py test dashboard.test_tracked_files dashboard.test_intake --noinput
.\.venv\Scripts\python.exe tools/test-intake-watcher.py
```

## Historical rehearsal, 16 October 2026

Windows local execution, 16 October 2026. All imported documents/accounts in automated tests are synthetic. The supplied Downloads image is a visual calibration reference, not an issued document or issuer trust anchor. No remote push, PR, tunnel or public deployment was performed.

## Git and environment

Freshly fetched `cf` and `origin/cf` both started at `b053b324e87d4a90f4d0151d3f7e7077759a89c5`, with zero divergence. The implementation lives on `feature/digilocker-assisted-intake` in `C:\Users\User\Downloads\Foliolet-digilocker-intake`. The original Evidentia checkout stays on `codex/foliolet-evidence-bridge` at `bcf7e724396c0d28341d7a4a4b7b09da1af1fae1`, retaining its untracked document/output. The existing cf checkout stays clean. Local main remains `c04741ee68563566dc82ab4e71b97c3898714f72`.

Java 17.0.19, Python 3.12, Node 25.9, Django 6.1, Tesseract 5.5.3; local PostgreSQL, EVM and private HTTP services use their own worktree state. Real Qwen inference was run first against the retained cloud-disabled service on 11434, then against the same hash-checked model copied into an owned CPU runtime on 11444 after the shared service disappeared. No model download or change to the original model/runtime was made. See [dependency record](DIGILOCKER_ASSISTED_INTAKE_DEPENDENCIES.md).

## Executed gates

| Gate | Observed result | Retained local evidence |
| --- | --- | --- |
| Full Java package, including opt-in live tests | PASS: 100 tests, zero failures/errors/skips | `.local-data/intake-java-final-build.log`, Surefire XML |
| Django dashboard, original and new tests | PASS: 72 | `.local-data/intake-django-final.log` |
| Native Windows companion unit tests | PASS: 11 | `.local-data/intake-watcher-tests.log` |
| Actual PowerShell companion launcher | PASS: 3 | `.local-data/intake-launcher-tests.log` |
| Original independent verifier/UI Node suite | PASS: 22 | `.local-data/intake-node-verifier.log` |
| Original Solidity/Ganache checks | PASS: authorization, immutable roots, assurance, supersession, revocation and seven Merkle shapes | `.local-data/intake-node-contracts.log` |
| Full private HTTP/watcher/vault/model/EVM flow | PASS: 46 | `.local-data/intake-live-final.log` |
| Real Edge user flow and captures | PASS: 11 | `.local-data/intake-ui-final.log` |
| Isolated failure backend, final packaged build | PASS: 12 | `.local-data/intake-failures-final.log` |
| CSV physical reading and manual fallback | PASS: 3 | `.local-data/intake-formats.log` |

The [machine-readable evidence](intake-demo/evidence.json) records the executed suite counts and individual live checks, with no credentials or bearer links. Synthetic browser captures show the [desktop enrollment](intake-demo/enroll-desktop.png), [mobile light review](intake-demo/review-mobile-light.png) and [mobile dark review](intake-demo/review-mobile-dark.png). These captures do not contain the supplied reference QR or a real issued document.

The 100-test Java invocation contains 93 standard tests and seven explicit live tests. Live tests include real inference with non-loopback Java networking denied, four real OCR/reading cases, the supplied wordmark at six scale/orientation combinations, and real Qwen source-aligned Math extraction. These are not counted again as independent additional tests. The standard suite retains 125-page accounting, 60/60 retrieval gold cases, 40/40 fine-print checklist passages, corrupt/protected/hostile PDFs, huge image dimensions/recursive forms, timeouts, cancellation, source/hash/owner rechecks and scratch cleanup. The historical 80-question application benchmark was not rerun or relabeled as current evidence.

Node 25 cannot load Ganache's optional native µWS binary; its existing JavaScript fallback was used and the contract test passed. No new native package was installed to suppress that warning.

## Exact commands

Run in the feature worktree. The [runbook](DIGILOCKER_ASSISTED_INTAKE_RUNBOOK.md) provides setup/start/stop and the default or owned model options. The full Java command below requires the existing reference image and healthy local model; its live tests must not silently skip.

```powershell
Set-Location 'C:\Users\User\Downloads\Foliolet-digilocker-intake'
$env:FOLI_TESSERACT='C:\Users\User\Downloads\Foliolet-testcloudflare\.local-tools\ocr\Library\bin\tesseract.exe'
$env:FOLI_OCR_DATA_DIR='C:\Users\User\Downloads\Foliolet-testcloudflare\.local-tools\ocr\share\tessdata'
$env:INTAKE_REFERENCE_IMAGE='C:\Users\User\Downloads\WhatsApp Image 2026-10-16 at 15.02.09.jpeg'
$env:FOLI_OLLAMA_URL='http://127.0.0.1:11444'
.\spring-boot-service\mvnw.cmd -f spring-boot-service/pom.xml -B '-Dtest=*Test,*Tests,*LiveIT' package
.\.venv\Scripts\python.exe django-service/manage.py test dashboard
.\.venv\Scripts\python.exe tools/test-intake-watcher.py
$env:NODE_PATH='C:\Users\User\Downloads\Foliolet-testcloudflare\spring-boot-service\node_modules;C:\Users\User\Downloads\Foliolet-testcloudflare\node_modules'
node --test spring-boot-service/scripts/test-proof-security.cjs spring-boot-service/scripts/test-verifier-ui.cjs
node spring-boot-service/scripts/test-contracts.cjs
```

Stop the owned demo before repackaging its JAR, and restart it with the newly built JAR. The final full package was built while only the separate owned model service was running. The following real HTTP gates then run sequentially against 8008/8088/55438/8548; they never target the original wallet's ports/data.

```powershell
.\.venv\Scripts\python.exe tools/make-intake-fixtures.py
.\.venv\Scripts\python.exe tools/test-intake-live.py
$env:FOLI_PLAYWRIGHT_MODULE='C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright'
node tools/test-intake-ui.cjs
.\.venv\Scripts\python.exe tools/test-intake-failures.py
.\.venv\Scripts\python.exe tools/test-intake-launcher.py
.\.venv\Scripts\python.exe tools/test-intake-live.py --formats-only
.\.venv\Scripts\python.exe tools/summarize-intake-evidence.py
```

The failure script creates another disposable database/vault and Java process on 8098, and uses 11439 for explicit local model doubles. It does not stop any shared Ollama service. Model refusal, missing OCR and process interruption are real failures. Missing/oversized/cloud-enabled metadata, forged values and delayed responses use a labeled local test double; no real 7 GB model was downloaded. Process restart is real, followed by a source-validated synthetic model-double retry.

## Coverage and adversarial cases

* **Watcher:** recursive final rename, `.crdownload`, old/hidden/unsupported files, native write lock, duplicate events, durable signed observation and upload retries, lost acknowledgments, orphan stage recovery, corrupt/refused outbox entries without blocking others, hash mismatch after observation, explicit session stop/expiry/re-arm, broad folders, symlink/native Windows junction escape, event/import bounds and fixed loopback/no-proxy/no-redirect transport.
* **Reading and indicators:** native, fully scanned, hybrid and last-page PDFs; logo-only, exact official-origin QR-only, both, neither and unrelated QR; forged visual positives stay provisional. Unit cases cover multiple QR, 130/260px scale, rotation, inversion, low-contrast/dark colors, cropped/blank/malformed codes and oversized pixels. Supplied wordmark calibration covers 0.7×/1×/1.6× and 90-degree rotation. Uninspected pages are inconclusive, not a clean negative.
* **Suggestions:** complete physical source lines, exact page/offset/hash, adjacent label/value binding, canonical decimal Math 90, score swaps, missing CGPA, invalid dates, percentages/units, numeric substrings/ranges, OCR O/0 and low-confidence words, ambiguous columns, corroboration on mixed OCR pages, malformed/oversized/duplicate model responses. Incorrect suggestions are discarded; accepted OCR text still carries transcription warnings.
* **Lineage:** canonical reorder remains unchanged; 90→95, changed label/type/path, addition and removal count as modifications; duplicates are rejected. The first encrypted baseline survives retries, a client cannot replace it or assert an unaltered flag, confirmation during inference cannot gain a late baseline, changed source/version cannot reuse old citations, and new versions have separate baselines.
* **Privacy/authority:** cross-owner session, observation, analysis, source and vault checks; capability cannot access full wallet endpoints; Origin/non-loopback use is refused; CSRF remains required for browser mutations; restricted receiver URLconf serves no intake/Foli routes or assets. QR URLs remain data and are never followed. Public exposure was tested locally against the restricted URLconf; no actual Cloudflare tunnel was opened.
* **Original behavior:** transient TXT suggestions, holder confirmation, salted Merkle commitments, anchoring/assurance codes, atomic version supersession, selective share, passive-GET refusal, one-time use, expiry, revocation, independent pinned verification and altered-proof rejection. General Foli chat, document citations and complete fine-print review are checked without granting mutation authority.

## Failures corrected during implementation

The negative evidence was used to repair implementation or harness errors, not converted into fabricated passes:

1. Percent fields initially collided with plain-value paths; deterministic unit-bearing paths fixed it. The real model sometimes returned scores as strings; numeric subject-score validation now determines decimal type from the exact source, preserving identifier strings.
2. The supplied small/rotated wordmark initially failed. Bounded crop upscaling, geometric calibration and rotation passes now pass all six reference variants. Native facts on mixed pages were initially rejected too broadly; only exact OCR-corroborated adjacent facts are now admitted.
3. Source preview and intake initially competed for Foli's reader gate and could immediately fail intake with BUSY. A bounded wait and concurrency regression test fixed that race. Enrollment's older synchronous PDF convenience parse was also removed so saved uploads acknowledge before bounded analysis.
4. Early browser assertions read hidden `innerText` or checked revocation before Stop completed. The harness now reads the correct DOM state and waits for the real stop response. Early proof-harness assumptions about passive GET status and revocation JSON were corrected to the actual unchanged APIs.
5. The shared Ollama on 11434 disappeared during a live scan run. Saved originals remained intact and explicit MODEL_OFFLINE/manual fallback worked. An isolated, hash-checked CPU copy on 11444 allowed continued testing without restarting or altering that shared service. Root cause of its disappearance was not established.
6. The first direct Foli POST in the new harness lacked the existing `X-Foli-Client: private` boundary header and correctly returned 403. The harness now supplies the header and retains a negative 403 control; production authorization was not relaxed.
7. PowerShell native daemon redirection initially held startup open; launching `pg_ctl` with redirected files and a bounded process wait fixed it. Stop explicitly accounts for Windows-owned console helpers while retaining command/PID/start-time guards. A UTC JSON-date conversion edge in the companion launcher was fixed and tested through the actual PowerShell process. A wording assertion was updated after the UI replaced implementation names with plain local-reading text.

Retained diagnostic examples include `.local-data/intake-live-model-disappeared.log`, `.local-data/intake-live-before-private-header-fix.log`, `.local-data/intake-scanned-diagnostic.log`, `.local-data/intake-startup-initial.log` and earlier component/UI logs. Private checkpoint/config files are intentionally ignored and must not be published; final durable evidence contains test names/counts, not passwords, pairing capabilities or bearer share URLs.

## Required acceptance matrix

Results below reflect the final packaged build and the completed live/browser/fault runs on 16 October 2026. “NOT TESTED” is retained for unavailable genuine authentication/documents and hardware.

| # | Requirement | Result | Evidence and boundary |
| --- | --- | --- | --- |
| 1 | Latest untouched cf base, fresh local feature branch, no push | PASS | Fresh fetch, zero divergence, separate worktree; original status and main/cf refs retained |
| 2 | Official separate HTTPS tab, manual official authentication | NOT TESTED | Link/no-opener/browser-close mechanics tested; automated browser intercepts the official tab. No real DigiLocker login/download performed |
| 3 | Opted-in recursive watcher imports finished exact bytes without duplicates | PASS | Real private watcher/HTTP/vault checks and 11 Windows tests; source retained |
| 4 | Manual upload with watcher disabled | PASS | Real HTTP manual import, model-failure fallback and actual Edge upload/review/confirmation |
| 5 | PDFBox/Tesseract reading or explicit gaps | PASS | Real native/scanned/hybrid fixtures, long/hostile reader regression, OCR manifests and page caps |
| 6 | QR/logo positive, negative and adversarial detection | PASS | Synthetic PDFs, six supplied-wordmark variants, dark/low-contrast/multiple QR; no issuer claim |
| 7 | Honest indicators, source assurance and self-enrolled fallback | PASS | UI/backend separate four concepts; real neither case remains SELF_ENROLLED |
| 8 | Local model suggestions with deterministic current source linkage | PASS | Real Math 90 decimal, missing CGPA discarded, citation/hash checks and forged/garbled negative tests |
| 9 | Editable UI Math 90, source links and OCR warnings | PASS | Actual Edge populated Math 90, opened the retained source page, displayed warnings, previewed Math 95 and showed the server-recorded modified state |
| 10 | Server-authoritative immutable baseline and modifications | PASS | Live edit/add/remove/reorder/client-flag/retry checks, canonical type/path/label tests and version/source isolation |
| 11 | Ownership/capabilities/sessions/paths/privacy/public isolation | PASS | Actual private HTTP controls, native Windows path tests, Django receiver negative route/static tests |
| 12 | Scanner/model/network/dependency failure with original/manual fallback | PASS | All twelve isolated fault checks passed against the final packaged build, including real restart and retry |
| 13 | Original Foliolet/Foli regressions | PASS | 100 Java, 72 Django, 22 Node and contract gate; live general chat, source-cited document answer and complete fine-print review preserved wallet/chain state |
| 14 | Consenting user-owned genuine DigiLocker PDF | NOT TESTED | None supplied; graphic reference and synthetic PDFs cannot substitute |
| 15 | Reproduced Windows setup and few-command operation | PASS | Own venv/dependencies, new database/EVM/vault, start/stop/restart, actual paired PowerShell launcher and explicit isolated CPU runtime |

## Remaining limitations

Issuer signature/provider verification is **not implemented**, by design. An exact official-domain QR can be fabricated; the graphic detector is a heuristic calibrated on a small reference/synthetic set. It can miss unfamiliar/recolored/low-quality logos and unsupported QR profiles. No genuine issuer-format corpus or OCR accuracy benchmark on real identity/education records was available. Only unambiguous colon/equal label/value lines produce automatic fields; free prose, ordinary multi-column CSV/tables and weak OCR may require manual entry. No coverage claim extends beyond reported processing budgets.

No official DigiLocker authentication, consented issued-document download or physical NFC read/write was performed. The real Edge test uses a clean synthetic profile and blocks unrelated network requests; its official-tab body is deliberately mocked, not a claimed government login. Accessibility checks cover labeled controls, keyboard focus and the accessibility tree, not a human screen-reader study. Fresh runtime installation on another Windows machine, public tunnel routing and production deployment were not tested. CPU speed varies and model cold starts can exceed a request budget; fallback/retry are intentional. Existing custodial key handling and development Ganache remain the prior local-demo architecture.

The one-minute demonstration and exact setup are in [the runbook](DIGILOCKER_ASSISTED_INTAKE_RUNBOOK.md). A future real issuer-verified badge requires a separately authorized provider/signed-payload integration with independently pinned issuer trust, supported schema/scope, expiry/revocation and audit evidence. Neither unchanged AI facts nor watcher continuity supplies that authority.
