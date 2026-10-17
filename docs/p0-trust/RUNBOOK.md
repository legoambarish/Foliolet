# PS32 local demonstration and reproducibility

Use the new branch only. Do not reset existing branches or reuse a different worktree's database, signing key or vault. Shared runtime **binaries** may be read; application state stays inside this worktree.

## Build and start on Windows

Prerequisites are the existing runbook's JDK 17+, Node, Python environment, PostgreSQL binaries, Tesseract and local Qwen model. Install the updated `tools/requirements-ocr.txt`, which now includes `zxing-cpp==2.3.0`, in the configured layout Python environment. The brand detector is packaged in the JAR. Keep the complementary worker next to `ocr-layout-worker.py`.

```powershell
# From the isolated Foliolet worktree. Stop its recorded services before rebuilding a JAR.
.\tools\stop-digilocker-demo.ps1
npm ci --ignore-scripts
npm ci --ignore-scripts --prefix spring-boot-service
node tools/build-frontend-assets.cjs
.\spring-boot-service\mvnw.cmd -f spring-boot-service/pom.xml -B package
$env:FOLIOLET_SHARE_MODE='local'
.\tools\start-digilocker-demo.ps1 `
  -RuntimeRoot 'C:\Users\User\Downloads\Foliolet-testcloudflare' `
  -SkipBuild -OllamaUrl 'http://127.0.0.1:11444' `
  -PgPort 55448 -EvmPort 8558 -ApiPort 8089 -UiPort 8018
```

The runtime path and Ollama port above are those verified on this machine; substitute your installed runtime on another machine. The added port arguments preserve existing defaults. Never start against occupied ports; the launcher refuses rather than stopping or reusing other services. `stop-digilocker-demo.ps1` checks its own worktree, recorded PID start time, command line and PostgreSQL directory. It retains all data. Do not rebuild over a running Windows JAR.

Open `http://localhost:8018/`. Register a disposable demo holder. The application uses the existing local Qwen model; no model download is triggered. The public receiver is not launched by these `local` instructions.

## Five-minute judge sequence

1. Upload a fictional PDF with the complete branding and supported structured QR. The supplied reference can be used locally, but do not publish or transmit its raw QR. Explain that the file is encrypted locally and issuer authority is unverified.
2. Wait for actual backend completion. Show separate green QR and branding stamps. A manual upload must not gain a watcher-import stamp. For an import demonstration, enable a dedicated folder, use the normal companion launcher, and create a new completed file after pairing; show the recorded import stamp.
3. Open a source citation. Explicitly review any uncertain OCR suggestion before accepting it. Confirm unchanged facts once; the modified stamp stays quiet. In a separate draft, edit Math from 90 to 95, or add/remove a field; confirm and show the server-computed modified state.
4. Anchor using the normal explicit control. Select only Math for disclosure. Check **Include document inspection status** only if QR/logo/PDF/import information should accompany that selected fact. Hidden fields and their history are not added.
5. Open the disclosure, then show the edited/unchanged selected-fact label, original suggestion's support, QR/logo checks and **Issuer not verified**. Use the normal independent verifier with separately provisioned deployment pins. Tampering with the exported status or fact fails verification.
6. Ask a source-grounded question in local Foli; click its exact citation. Run whole-document review and show the early checklist while semantic review proceeds. Repeating the identical review on an unchanged authorized version reuses its bounded result. Do not promise every new CPU question is instant.

## Optional Gemini setup

Default-off local functionality is the demonstrated default. The provided key was tested only on fixed fictional material. Before enabling real application use, the operator must independently establish active paid-service terms and appropriate authorization. Do not infer this from successful generation, model listing or a response's service-tier label.

Set the following **outside Git** and restart the backend only after that review:

```text
FOLI_GEMINI_ENABLED=true
FOLI_GEMINI_DATA_POLICY=paid-reviewed
FOLI_GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=<server-side secret supplied securely>
```

The user must then select the per-request checkbox in Ask Foli. Questions, history and selected text excerpts are sent; originals/images stay local. Review and extraction remain local. A missing/unreviewed configuration keeps the option unavailable. A provider outage reports fallback to local; it does not authorize broader data release. Never put the key in a browser setting, proof, `.env.example`, screenshot, command output or committed file. Compose forwards these optional variables with disabled/empty defaults; its runtime was configuration/unit-tested, not daemon-booted in this run.

## Reproduce checks

```powershell
.venv\Scripts\python django-service/manage.py test dashboard --noinput
npm run test:verifier
npm run test:contracts
.venv\Scripts\python tools/test-container-runtime.py
docker compose config --quiet
.venv\Scripts\python tools/make-intake-fixtures.py
$env:INTAKE_TEST_API='http://127.0.0.1:8089'
$env:INTAKE_TEST_UI='http://127.0.0.1:8018'
$env:INTAKE_TEST_RPC='http://127.0.0.1:8558'
$env:INTAKE_TEST_DSN='host=127.0.0.1 port=55448 dbname=wallet_intake_demo user=wallet'
.venv\Scripts\python tools/test-intake-live.py
.venv\Scripts\python tools/test-p0-status-live.py
.venv\Scripts\python tools/test-p0-recipient-browser.py
```

For the supplied image, append `--reference <absolute-local-image-path>` to `test-p0-status-live.py`. It embeds that image into a fictional PDF; the image/payload stays in ignored local state and is never sent to Gemini. The script creates fresh disposable accounts and grants. It uses the actual backend, vault, chain, strict Django profiles and CSRF, not fake verification responses. Recipient browser testing uses a transient loopback Waitress server and locally routed HTTPS, not an externally published Cloudflare tunnel.

For sender UI checks, set `FOLI_PLAYWRIGHT_MODULE` to an installed Playwright Node module (this run used `.venv/Lib/site-packages/playwright/driver/package` from Python Playwright 1.58.0), then run `node tools/test-intake-ui.cjs`. Edge is launched headlessly with fresh disposable profiles. For the 51-check wallet suite, set `WALLET_TEST_API`, `WALLET_TEST_UI` (use `http://localhost:8018` to match generated share URLs), `WALLET_TEST_RPC`, `WALLET_TEST_DSN`, then run `tools/test-live-workflow.py`.

For before/after extraction, retain the baseline's `target/classes` **before** compiling the new version in a separate baseline checkout. Build the test harness and dependency classpath with Maven `test-compile dependency:build-classpath -Dmdep.outputFile=target/p0.classpath`. Configure `FOLI_TESSERACT`, `FOLI_OCR_DATA_DIR`, `FOLI_LAYOUT_PYTHON`, `FOLI_LAYOUT_SCRIPT`, then run:

```powershell
.venv\Scripts\python tools/benchmark-p0-intake.py --baseline-classes <retained-baseline-classes>
.venv\Scripts\python tools/benchmark-p0-jobs.py
```

Run comparable extraction trials sequentially while other test/model workloads are idle. Cold JVM trials do not imply a cold model, cold OS disk cache or cold provider. `benchmark-p0-providers.py --help` describes the fixed fictional provider rubric. `P0GeminiSmokeMain` uses only hardcoded fictional text with the actual Java adapter; its test policy gate is not an assertion about your account and must not be copied into application configuration. Raw reports remain ignored. Commit only sanitized metrics and fictional fixture definitions.

The test scripts intentionally retain disposable accounts, proofs, DB/chain state and screenshots for debugging. They do not clean user data. Stop the isolated demo with its guarded script when finished.
