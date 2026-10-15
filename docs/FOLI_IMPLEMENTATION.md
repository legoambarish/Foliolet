# Foli: private local reading assistant

Implemented on the existing lowercase `cf` branch in `C:\Users\User\Downloads\Foliolet-testcloudflare`, beginning at `504a1872cb921c40e9420df4ab1718aa43a52069`. The Evidentia worktree was inspected but not edited. `main` remains at `c04741ee68563566dc82ab4e71b97c3898714f72`. No reset, merge, remote push or public deployment is part of this implementation. Both supplied research/master-prompt documents were read completely; the direct implementation request supersedes their historical plan-only instructions.

Phases 0–5 are documented in [baseline](FOLI_PHASE_0.md), [reading](FOLI_PHASE_1.md), [Q&A](FOLI_PHASE_2.md), [review](FOLI_PHASE_3.md), [interface](FOLI_PHASE_4.md) and [hardening](FOLI_PHASE_5.md), with a separate [evaluation](FOLI_EVALUATION_2026-10-15.md) and [demonstration](FOLI_DEMO.md). Runtime data, synthetic test accounts, model weights, captures and full raw receipts remain ignored under `.local-data/foli/`; no credentials or private customer document text are committed.

## Start this existing checkout

Use separate PowerShell terminals. Keep the existing database, vault keys, relay key and chain state. Do not reinitialize, delete or replace them. All five service listeners were verified on numeric loopback.

```powershell
Set-Location C:\Users\User\Downloads\Foliolet-testcloudflare
git branch --show-current          # must say cf; stop if it does not
```

PostgreSQL is already running on `127.0.0.1:55432`. If it is stopped, this checkout's retained cluster can use the existing portable binaries without changing their worktree:

```powershell
.\tools\start-postgres.ps1 -PostgresBin 'C:\Users\User\Downloads\Evidentia\.local-tools\postgres\bin'
```

Alternatively install this checkout's own pinned binary copy once with `tools/setup-local-postgres.ps1`, then use `tools/start-postgres.ps1`. The existing launcher checks the retained cluster rather than resetting it. Its trust authentication is a local development setting.

Start the remaining terminals from the same `cf` root:

```powershell
# Terminal 1: retain the existing persistent local chain on port 8545
npm run evm

# Terminal 2: local Ollama on 11434, cloud disabled, no automatic downloads
.\tools\start-foli-ollama.ps1

# Terminal 3: private Spring service on 8080
.\tools\start-foli-backend.ps1

# Terminal 4: private Django application on 8000
.\tools\start-foli-frontend.ps1
```

If a service is already listening, reuse it; do not launch a duplicate. Open [Ask Foli](http://127.0.0.1:8000/ask-foli/) and sign in with your Foliolet account. The Foli frontend launcher selects the existing explicit local sharing mode for that terminal; it does not start a tunnel or modify receiver configuration. Existing Cloudflare launchers remain available separately. Stop foreground services with Ctrl+C. Use the existing PostgreSQL shutdown procedure in [RUN_GUIDE.md](RUN_GUIDE.md); preserve its files.

## One-time setup and reproducibility

This machine has Java 17.0.19, Python 3.12, Node 25.9, a Ryzen 7 7435HS, 23.69 GiB usable RAM and an RTX 4060 Laptop GPU with 8188 MiB VRAM. The Maven wrapper and existing local development dependencies are already installed. For a new environment follow the existing [run guide](RUN_GUIDE.md), retaining the reviewed application configuration and trust provisioning. Foli does not manufacture a replacement vault key or registry identity.

```powershell
.\.venv\Scripts\python.exe -m pip install -r django-service/requirements.txt -r tools/requirements-dev.txt
.\.venv\Scripts\python.exe tools/setup-foli-runtime.py
```

The explicit setup downloads checksum-verified Ollama **0.40.3** and an isolated **Tesseract 5.5.3** environment. OCR's 31 exact Windows builds/checksums are pinned in `tools/foli-ocr-win64.lock`; an offline dry run resolved all 31 from the measured cache. TLS verification stays enabled. Setup is idempotent, never invoked by app startup and downloads no customer documents. See [dependency receipts](FOLI_DEPENDENCIES_2026-10-15.md).

With the Ollama terminal running, pull the selected model once if missing:

```powershell
$env:OLLAMA_HOST='127.0.0.1:11434'
$env:OLLAMA_MODELS=Join-Path (Get-Location) '.local-data\foli\models'
.\.local-tools\ollama\ollama.exe pull qwen3:4b-instruct
Invoke-RestMethod http://127.0.0.1:11434/api/status
.\.local-tools\ollama\ollama.exe list
```

Require `cloud.disabled=true`; the installed model digest is `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`, package **2,497,293,803 bytes**, Q4_K_M, Apache-2.0. Package size differs from runtime RAM/VRAM. The comparison ran Gemma 3 4B, Qwen 2.5 7B and Qwen 2.5 3B; the smaller 3B candidate failed quality/format checks. No cloud or larger-model fallback is configured. Installing candidates is optional and explicit; retain their separate license terms.

The runtime launchers set `OLLAMA_NO_CLOUD=1`, host `127.0.0.1:11434`, context 8192, one parallel generation, one loaded model, queue four and ten-minute keep-alive. Spring pins **Spring AI 2.0.1** without starters, tools, advisors, vector databases or automatic model pulls. It validates actual cloud-disabled status and the installed tag's positive size strictly below 6,000,000,000 bytes before each inference. Model changes require backend restart with `start-foli-backend.ps1 -Model 'installed-tag'`; changing the tag does not imply it has passed these benchmarks.

## Reading and answer behavior

The authenticated source picker lists only permitted existing documents. Wallet originals require owner access even for ADMIN, AES-GCM authentication and the retained Keccak hash. Legacy originals use uploader/ADMIN policy and a distinct storage root. Foli never invokes the legacy verify/restore path, enrollment, anchoring, disclosure, approvals or repository save operations. Every cache access, job publication/poll and source image/text request reopens and reauthorizes the original, checking version and SHA-256. Lost access, replacement, tampering and deletion fail closed; Foli does not restore a damaged original.

PDF, UTF-8 TXT and CSV are supported. Text files retain physical lines and delimiters; CSV segment locations are not parsed spreadsheet row identities. Other types, including DOCX, are explicitly unsupported. A password-protected PDF needs a readable original supplied through the existing document workflow; Foli has no password-removal operation.

PDFBox **3.0.8** extracts each digital page. Suspicious text, scans, image/text mixtures and form widgets trigger local per-page Tesseract OCR, including rotation recovery. OCR records confidence, word offsets/boxes and transcription warnings. Tiny print, multiple columns/tables, dynamic forms, ignored actions and embedded attachments have visible coverage warnings. Attachments are not recursively read. Preview uses a rendered original PNG, while quote highlighting applies to extracted text; no pixel-perfect PDF highlight is promised.

Original bytes enter a dedicated child JVM over a pipe, with a 512 MiB heap and bounded output/time. The child starts no Spring context, DB client or model client; it inherits an allowlist of basic process environment variables, excluding application credentials. OCR scratch files are confined to a new per-job directory and removed after success, failure or cancellation. The parent kills the reader and observed OCR descendants on timeout/cancellation. This is resource isolation, not a complete operating-system sandbox against arbitrary native-code exploits. A forced host crash may leave private scratch files; the application does not recursively clean unknown directories.

General conversation needs no document. Document Q&A uses exact/lexical retrieval, requested headings and referenced definitions/schedules, then bounded evidence context. Repeated boilerplate is suppressed, and each answer uses compact local evidence IDs tied to immutable page/offset/hash metadata. No embedding model was added without a measured benefit. Unusual explanations/analogies are accepted. Requested writes receive an explanation of Foli's read-only boundary; the model has no executable tools regardless of prompt wording.

**Review fine print** is a separate complete-source mode: every readable chunk receives a deterministic twelve-category scan, followed in source order by bounded semantic map batches and reduction. It covers renewal, termination, fees, changes, liability/indemnity, warranties, disputes, privacy, deadlines, definitions, exceptions/conflicts and schedules/footnotes. Findings link exact text, definitions and references; missing headings and possible conflicts remain explicit. Checklist coverage and successful semantic coverage are reported separately. A failed model batch retains checklist findings and marks partial interpretation.

Every displayed source quotation is verified server-side against the permitted extracted page's exact offsets. Unknown IDs and invented quotations are omitted. The badge establishes alignment to that transcription; it does not establish that the model's claim follows from it, that OCR is correct, that a document is authentic or that a term is enforceable. Generated interpretations can still be wrong or omit a relevant exception. Targeted chat is not an exhaustive absence search. Use the coverage panel, whole-document review and original viewer for material decisions.

## Privacy and operating limits

Foli's browser routes are private-only `/ask-foli/` and `/ask-foli/api/...`; Spring uses `/api/foli/...`. Both require current authentication. Unsafe requests require Django CSRF and Spring's private-client header; Spring refuses browser Origin headers. Public receiver URLconf/static allowlists were not extended. The Foli proxy accepts only fixed loopback routes, disables environment proxies/redirects and has no stub/default-credential fallback. Strict self-only CSP and DOM text rendering prevent model-generated HTML, links and images from executing.

Conversation stays visibly in the current tab. It is cleared on source switching, sign-out/authorization loss, navigation/reload or **Clear**. There is no localStorage/IndexedDB chat persistence, durable server history or embedding store. Clear also cancels/removes the current user's server jobs/cache. Bounded extracted-text cache and job results expire after ten minutes; JVM/OS memory is not secure-erased. Ollama may retain its active context in RAM during keep-alive. Document originals continue to follow the existing vault retention policy. Request/prompt/source bodies are excluded from new application logging; canary checks covered the private Java/Django logs.

| Budget | Default behavior |
| --- | --- |
| Original | 20 MiB maximum |
| Pages | 200 processed; every skipped page accounted up to a 5000-page rejection ceiling |
| Text | 1.5 million characters/document; 100,000/page; oversized text explicitly skipped |
| Rendering | 8 million output pixels; decoded-image/form preflight plus child heap boundary |
| OCR / extraction / preview | 25 s/page, 180 s/reader, 30 s/preview |
| Model | 8192-token context, 900 output tokens, 120 s/request |
| Context | Conservative UTF-8 byte upper bound including system/template/output reserve; omitted context warned |
| Jobs | One worker, queue four, two active/user, ten starts/minute/user, 32 retained results |
| HTTP / job lifetime | Four simultaneous private requests, 32 KiB JSON, five-minute active-job deadline |
| RAM cache/history | Eight snapshots and four million characters; six bounded turns, 3000 history characters |

Limits intentionally favor explicit partial results over exhausting this laptop. Returned states include offline/missing/cloud-enabled/oversized model, corrupt/protected/unsupported file, source/access changes, unreadable OCR, reader resource/time failure, busy/rate-limited, cancelled and no supporting citation. The UI offers retry, Stop, source navigation and per-page coverage. Responses appear after citation checks with progress; token streaming was not enabled.

## Repeat validation

Run from the `cf` root with the services above. The live scripts create only fresh synthetic users/documents, never reuse a real customer's original. They retain test evidence locally. The existing wallet regression scripts exercise their own synthetic writes/chain transactions to verify unchanged trust workflows; Foli itself performs no such operations.

```powershell
.\spring-boot-service\mvnw.cmd -f spring-boot-service/pom.xml test
.\.venv\Scripts\python.exe django-service/manage.py test dashboard
npm run test:verifier
npm run test:contracts
.\.venv\Scripts\python.exe tools/make-foli-fixtures.py
.\.venv\Scripts\python.exe tools/test-foli-reading.py
.\.venv\Scripts\python.exe tools/benchmark-foli-reading.py
.\.venv\Scripts\python.exe tools/test-foli-qa.py --output repeated-qa.json
.\.venv\Scripts\python.exe tools/test-foli-review.py
.\.venv\Scripts\python.exe tools/test-foli-adversarial.py
.\.venv\Scripts\python.exe tools/test-live-workflow.py
.\.venv\Scripts\python.exe tools/test-live-security.py
```

The completed release records 78/80 strict application rubric passes, 40/40 authored fine-print passages, 125/125 semantic chunks and exact alignment of every returned quote. The two remaining chat rubric misses and raw-model conflict failures are retained in the evaluation. An actual Ollama stop/restart also verified an OFFLINE job error and successful recovery. Do not stop a runtime while someone has active work; `test-foli-outage.py --offline`/`test-foli-outage.py` only verify an intentionally stopped/restored service and never stop it themselves.

Fixture generation additionally requires `pip install -r tools/requirements-foli-test.txt`. Run real OCR/offline inference tests explicitly (the network guard is Java-17 test-only):

```powershell
$env:FOLI_TESSERACT=Join-Path (Get-Location) '.local-tools\ocr\Library\bin\tesseract.exe'
$env:FOLI_OCR_DATA_DIR=Join-Path (Get-Location) '.local-tools\ocr\share\tessdata'
.\spring-boot-service\mvnw.cmd -f spring-boot-service/pom.xml '-Dtest=FoliOcrLiveIT,FoliLocalLiveIT' test
```

For browser validation use Playwright 1.62.1 with installed Edge (the browser library is a test dependency, not a product runtime dependency):

```powershell
$env:NODE_PATH='C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
node tools/test-foli-ui.cjs
```

Use a separate terminal for model comparison after installing optional candidates; it unloads/reloads models, so run it without interactive Foli work:

```powershell
.\.venv\Scripts\python.exe tools/benchmark-foli-models.py --output .local-data/foli/repeated-model-benchmarks.json
```

`tools/measure-foli-resources.py` samples OS/process RAM during a real 125-page review using the synthetic UI fixture. The fresh-runtime measurement peaked at 2.328 GiB in the native runner; an earlier extended mixed test session observed 8.493 GiB with the cause unresolved. Package size is not a runtime memory ceiling; keep available RAM in view during extended use. The evaluation retains both observations.

The application successfully inferred with Java non-loopback connects denied and Ollama cloud disabled; CPU-only generation also ran with measured zero model VRAM. Physical adapter disconnection and a full OS-level native-process egress sandbox were not performed. These limits, benchmark misses, OCR sample scope and raw negative results are recorded in the evaluation, rather than presented as universal reliability claims.
