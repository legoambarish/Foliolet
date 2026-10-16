# State-safe setup and grand-finale demonstration

## 1. Read this before starting

Use the new branch in a separate directory. Never delete `.local-data`, replace encryption/signing keys, reset Ganache, clear PostgreSQL or overwrite deployment pins to repair an error. The original `main`, `cf` and DigiLocker worktrees are not targets for these commands. Only fictional documents belong on the presentation screen.

Verified runtime family: Java 21, Python 3.13, Node 22, PostgreSQL 17 in Linux CI, Tesseract 5.3.4 and bundled Chromium. Windows Django/launcher results are listed in final acceptance evidence; launcher parsing is not the same as a complete Windows PostgreSQL/EVM run. The repository's Compose file is **`compose.yaml` and provisions PostgreSQL only**, not the full application. Its database/port settings differ from the isolated demo below.

The core demo does not require Ollama, internet access, an API key or DigiLocker organizational approval after dependencies and fixtures are installed. Optional OCR engines improve scans; missing services must produce explicit limitations. Local Foli is optional and can be slow on CPU. Do not make a live model response the critical path of the presentation.

## 2. Obtain the implementation without disturbing another worktree

```text
git clone --branch feature/ps32-final-winning-audit-20261016-1645 --single-branch https://github.com/legoambarish/Foliolet.git Foliolet-PS32
cd Foliolet-PS32
git status --short
git rev-parse HEAD
```

Record the revision used for the presentation. Use the final acceptance commit as a reproducible reference; later documentation-only commits need not change application behavior. Do not merge into the original branch as part of setup.

## 3. Windows installation and startup

In PowerShell from the new repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r django-service\requirements.txt -r tools\requirements-dev.txt -r tools\requirements-foli-test.txt -r tools\requirements-ocr.txt
npm ci
npm --prefix spring-boot-service ci
npm run contracts:build
.\.venv\Scripts\python.exe tools\make-ocr-benchmark.py
.\.venv\Scripts\python.exe tools\make-intake-fixtures.py
```

Java and Node must be on PATH. The launcher expects reusable PostgreSQL binaries under `.local-tools\postgres\bin` and optional Tesseract under `.local-tools\ocr`. The repository's existing installers may supply those dependencies; do not download unverified binaries or replace a working runtime merely to match a path.

When those binaries already exist in another Foliolet directory, pass that directory as `RuntimeRoot`. It supplies reusable tool binaries; this launcher creates/uses the **new worktree's** `.local-data` and refuses occupied demo ports. Example:

```powershell
.\tools\start-digilocker-demo.ps1 -RuntimeRoot 'C:\path\to\existing\Foliolet' -MaxHeapMb 768
```

When dependencies are in the new directory itself:

```powershell
.\tools\start-digilocker-demo.ps1 -MaxHeapMb 768
```

Do not pass `-SkipBuild` until the current revision has been built. The repaired guard permits the exact isolated audit branch as well as the original dedicated DigiLocker branch family; it does not authorize running from `main` or `cf`. Default maximum JVM heap is 768 MiB, configurable from 512 to 4096 MiB. That does not include OCR/model/OS memory.

The launcher starts its owned PostgreSQL/EVM/backend/frontend processes, applies Django migrations and provisions trust pins from the local deployment record. It does not silently accept mismatched retained pins. The private UI is on port 8008, Spring on 8088, EVM on 8548 and PostgreSQL on 55438.

Optional local model origin must be numeric loopback, for example `-OllamaUrl 'http://127.0.0.1:11434'`. Model download/installation is a separate explicit action. No hosted AI key is required; keep `DMS_EXTERNAL_AI_ENABLED` unset/false.

## 4. Health checks and safe shutdown

```powershell
Invoke-RestMethod http://127.0.0.1:8088/api/public/network
(Invoke-WebRequest http://127.0.0.1:8008/login/).StatusCode
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 55438,8548,8088,8008
.\tools\stop-digilocker-demo.ps1
```

The stop script uses recorded PID/start-time/worktree ownership and the owned PostgreSQL data directory; it refuses ambiguous unrelated processes. It retains keys, database, vault, model files and chain history. A port conflict is a reason to identify the owning process, not to kill every Java/Node/Python process.

Before a real migration, make an offline backup of the private data and its associated keys using an access-controlled destination. A backup without the matching encryption/signing/deployment state is not a full recovery plan. Session encryption accepts legacy signed JSON, but rewriting old rows is explicit:

```powershell
Push-Location django-service
..\.venv\Scripts\python.exe manage.py reencrypt_sessions --dry-run
..\.venv\Scripts\python.exe manage.py reencrypt_sessions
Pop-Location
```

The command preserves session IDs and expiry and avoids overwriting concurrently changed rows. Do not rotate the Django key as a substitute for migration.

## 5. Linux reproduction

The authoritative executed Linux recipe is [the full-stack workflow](../../.github/workflows/ps32-full-stack.yml), with exact environment, versions, service ports, build commands and evidence collection. It is a real PostgreSQL/Ganache/Spring/Django/Chromium run, not a mocked integration test.

For a manual private demo, use a fresh clone and isolated state. Install Java 21, Node 22, Python 3.13, Docker, Tesseract English and DejaVu Sans through your normal trusted package manager. Then:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r django-service/requirements.txt -r tools/requirements-dev.txt -r tools/requirements-foli-test.txt -r tools/requirements-ocr.txt
npm ci
npm --prefix spring-boot-service ci
npm run contracts:build
(cd spring-boot-service && bash mvnw -B -DskipTests package)
python tools/make-ocr-benchmark.py
python tools/make-intake-fixtures.py
```

Use a dedicated PostgreSQL instance for `wallet_intake_demo`, role `wallet`, on loopback port 55438. The CI's trust-authentication setting is for an ephemeral fixture only; a reusable database should use an explicit password. Export the corresponding JDBC credentials and these demo settings in the shell that starts services:

```bash
export NODE_PATH="$PWD/spring-boot-service/node_modules"
export SERVER_ADDRESS=127.0.0.1 SERVER_PORT=8088
export SPRING_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:55438/wallet_intake_demo
export SPRING_DATASOURCE_USERNAME=wallet
export BLOCKCHAIN_RPC_URL=http://127.0.0.1:8548 BLOCKCHAIN_CHAIN_ID=1337
export WALLET_SHARE_BASE_URL=http://127.0.0.1:8008
export SPRING_BOOT_API_BASE_URL=http://127.0.0.1:8088 PUBLIC_EVM_RPC_URL=http://127.0.0.1:8548
export FOLIOLET_SHARE_MODE=local
export FOLI_LAYOUT_PYTHON="$PWD/.venv/bin/python" FOLI_LAYOUT_SCRIPT="$PWD/tools/ocr-layout-worker.py"
```

Start `node tools/digilocker-evm.cjs` in an owned terminal. It creates/uses this worktree's development relay and chain state. After it is ready, read the relay key only into the backend environment, never print or publish it:

```bash
export BLOCKCHAIN_PRIVATE_KEY="$(cat .local-data/development-relay.key)"
(cd spring-boot-service && java -Xmx768m -jar target/dms-0.0.1-SNAPSHOT.jar)
```

After backend health succeeds, run `node tools/provision-digilocker-trust.cjs`. Then, in the same configured environment, run `python manage.py migrate --noinput` from `django-service` and `python manage.py runserver 127.0.0.1:8008 --noreload`. Stop only the owned terminal processes. Do not invoke the destructive CI resilience script against a personal runtime; it intentionally requires a GitHub Actions fixture and the exact owned database container.

macOS dependency paths and full service startup were not executed in this run. Cross-platform font selection and Python code are not equivalent to a tested macOS deployment. Containerized Linux reproduction is the established fallback.

## 6. Regression and diagnostic commands

```text
cd spring-boot-service
mvnw.cmd test                 # Windows
bash mvnw test               # Linux
cd ../django-service
python manage.py test --noinput
python manage.py check
cd ..
npm run test:contracts
npm run test:verifier
```

The contract suite uses disposable state. Live scripts can create and deliberately corrupt their own test records; use them only in the isolated environment documented by the workflow. Relevant scripts: `test-live-workflow.py`, `test-live-security.py`, `test-ocr-intake-ui.cjs`, `test-intake-failures.py`, `ps32-signature-ui.cjs`, `ps32-live-checks.py`. The last one deliberately stops and restarts its owned database/EVM/backend.

Controlled document evaluation uses `ps32-benchmark.py` with explicit source, cases, corpus root and output path. It never scans a private document inventory implicitly. Public CORD acquisition is `ps32-public-corpus.py`; original annotations and attribution are retained. A null metric for an unmapped schema must not be converted to zero or 100%.

## 7. Finale walkthrough

**Opening:** “A verifier needs one fact. Why should a student send an entire marksheet? Foliolet lets us share the selected fact and show exactly what has—and has not—been verified.”

Use a clearly fictional, realistic table-heavy marksheet with more data than the recipient needs. Upload it, show the original, inspect the proposed field's source support and review state, and confirm only the intended facts. Explain that the human review is part of the system rather than concealing it.

Anchor the commitment. Show that no original document or full plaintext claim list is placed on-chain. Create a selective disclosure and open the recipient view. Display independent verification and the separately pinned deployment. Export the selected proof and show that undisclosed values/salts are absent.

Change a selected claim in a copied proof. Run the verifier and show rejection. Revoke a grant or demonstrate one-time release; explain that revocation prevents future authorized access, not recall of already copied information.

For the new trust demonstration, inspect three fictional PDFs: unsigned; correctly self-signed; changed after signing. The genuine self-signature can pass mathematics while the UI still says issuer authenticity is not established. The tampered file fails the signed-byte check. This is a more credible moment than claiming every uploaded certificate is authentic.

Close: “The innovation we are demonstrating is the workflow from source evidence to minimal disclosure with honest assurance—not a claim that blockchain turns a false document into a true one.”

## 8. Fallback and hardware boundaries

Prefer the local native-PDF route for the critical demo. Keep a scanned example ready to show review-required behavior, not instant universal extraction. Keep Ollama optional; the real CPU model had material latency and citation errors. Pre-download dependencies/models/fixtures; no internet is needed for local proof checks against the running local chain.

A saved video may be used only with a visible “prerecorded” label. Do not present screenshots or previous test output as a live successful action. Preserve the actual CI evidence as a fallback explanation, not a substitute claim that the current laptop has passed all tests.

NFC may open the same disclosure URL on a compatible phone. The URL remains a bearer capability and can be copied; an NFC tap is neither issuer authentication nor recipient identity. Physical NFC/mobile and public Cloudflare tunnel behavior were not established by this run. Use them only after a real device rehearsal; otherwise demonstrate the same URL/QR through the verified browser path.
