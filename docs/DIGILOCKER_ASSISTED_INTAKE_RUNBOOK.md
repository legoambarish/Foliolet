# Windows assisted-intake runbook

Tested on 16 October 2026 with Windows PowerShell 7, Java 17.0.19, Python 3.12 and Node 25.9. All commands below run from the new feature worktree. Nothing is pushed. The original Evidentia checkout and `cf` checkout keep their own state.

**Normal use now requires one desktop action:** double-click **Foliolet** on the Windows desktop, or `Foliolet.vbs` in this checkout. It handles local setup/startup and opens the browser. See the [desktop launcher guide](FOLIOLET_DESKTOP_LAUNCHER.md) for the Start/Stop window. The commands below remain available for developers and diagnostics.

## One-time setup on this machine

```powershell
Set-Location 'C:\Users\User\Downloads\Foliolet-digilocker-intake'
git branch --show-current
# Must show feature/digilocker-assisted-intake.
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r django-service/requirements.txt -r tools/requirements-dev.txt -r tools/requirements-foli-test.txt
New-Item -ItemType Directory -Path "$env:USERPROFILE\Downloads\Foliolet Intake" -Force
```

The existing `C:\Users\User\Downloads\Foliolet-testcloudflare` contains the portable PostgreSQL binaries, Tesseract/trained data and Node packages used in the reproduced run. The launcher reads those immutable runtime files; it creates all databases, vaults, keys and chain state inside this new feature worktree's ignored `.local-data` directory. It refuses occupied ports instead of reusing or stopping an unrelated service.

Check the existing local model without downloading anything:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/status
(Invoke-RestMethod http://127.0.0.1:11434/api/tags).models |
    Where-Object name -eq 'qwen3:4b-instruct' |
    Select-Object name,size,digest
```

The tested runtime reports `cloud.disabled = true`, model package 2,497,293,803 bytes, digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`. A missing/offline model leaves original storage and manual fact entry available. Startup never downloads or starts Ollama. Starting an independently installed Ollama is an explicit operator step; configure `OLLAMA_NO_CLOUD=1` in that server's environment. The existing Foli preflight also rejects missing, cloud-enabled or oversized model metadata.

The shared service on 11434 disappeared during an initial acceptance run. For the completed rehearsal, the following explicit option copies only the retained selected model and CPU runtime into this feature worktree, verifies every model blob against its digest, and starts an owned CPU-only service on 11444. It downloads nothing, preserves the original runtime/model files and avoids the GPU being used by another workload. Allow about 2.6 GB additional disk space. The model helper is optional and uses the same tag/package, not a second model.

```powershell
.\tools\start-digilocker-model.ps1 -RuntimeRoot 'C:\Users\User\Downloads\Foliolet-testcloudflare'
.\tools\start-digilocker-demo.ps1 -RuntimeRoot 'C:\Users\User\Downloads\Foliolet-testcloudflare' -SkipBuild -OllamaUrl 'http://127.0.0.1:11444'
```

Build once before using `-SkipBuild`, with `.\spring-boot-service\mvnw.cmd -f spring-boot-service/pom.xml -B package`. `stop-digilocker-demo.ps1` also stops this optional owned model process using its separate process manifest, while retaining the copied files. The shared service on 11434 is never stopped by these helpers. CPU selection follows the [upstream Ollama GPU configuration](https://github.com/ollama/ollama/blob/main/docs/gpu.mdx).

## Start and stop

```powershell
.\tools\start-digilocker-demo.ps1 -RuntimeRoot 'C:\Users\User\Downloads\Foliolet-testcloudflare'
# After a successful build, subsequent starts can use -SkipBuild.
```

Open **http://127.0.0.1:8008/** and register/sign in with a disposable holder account for a demonstration. The launcher prints readiness and writes timestamped service logs. It does not open a tunnel. Its operator trust provisioning checks the isolated contract address/code and operator against its own local deployment; it never trusts a bundle-supplied root.

| Service | Dedicated endpoint/state |
| --- | --- |
| Private Django | `127.0.0.1:8008` |
| Private Spring | `127.0.0.1:8088` |
| Demo EVM | `127.0.0.1:8548`, chain 1337 |
| New PostgreSQL cluster | `127.0.0.1:55438`, database `wallet_intake_demo` |
| Ollama | Existing `127.0.0.1:11434`, or explicit owned CPU copy on `127.0.0.1:11444` |
| New private state | This worktree's `.local-data` |

```powershell
.\tools\stop-digilocker-demo.ps1
```

Stop checks PID, start time and process command/worktree before stopping only its own managed process trees, optional owned model and exact PostgreSQL data directory. It preserves every database, original, proposal, chain file and key. It leaves shared Ollama and unrelated applications alone. Start/stop/restart was reproduced. Do not delete `.local-data` to fix a problem: that would discard the new demo's evidence and keys. A failed startup can leave some of its own services running; use this same stop helper and inspect the logs before restarting.

## Five-step user flow

1. On **Enroll**, select **Import from DigiLocker**. A separate official HTTPS tab opens with no opener. Log in there yourself and choose **Issued Documents**. Foliolet receives no DigiLocker login or OTP. For automatic import, pair the folder in step 2 before downloading.
2. For automatic import, first expand **Use an optional local folder watcher**, choose a dedicated absolute folder, tick consent and select **Enable folder intake**. Save the pairing download. Run the command below once from this feature checkout, then download into the chosen folder. The selected folder must already exist.
3. Foliolet shows **Documents in your watched folder**, listing completed PDF/TXT/CSV files from the current paired folder and its subfolders, newest modified first. The list refreshes every two seconds while Enroll is open; added, changed and removed files update automatically. Select a row to import those exact bytes and review facts. Files already imported by the watcher open their saved document. Check coverage and OCR warnings against the original.
4. Review/edit/add/remove facts, then tick the confirmation checkbox and select **Confirm facts**. The preview is checked again on the server. `Math: 90` changed to `95` is **Facts edited since extraction**; an identical reordered set is **AI-suggested facts unchanged**.
5. Explicitly **Anchor**, then use the existing **Share** flow to choose only the facts to disclose. Recipient proof verification and lifecycle checks remain the existing protocol. **Issuer not verified** stays separate from all local indicators and lineage labels.

```powershell
.\tools\start-digilocker-watcher.ps1 -Background
```

The launcher selects the latest `foliolet-intake.json` / `foliolet-intake (n).json` download, or opens a file picker if it cannot find one. It rejects expired pairing files and restricts its own state folder to the current Windows account. You never need to open/edit JSON. If the file was saved elsewhere, select it in the picker or provide its path with `-PairingFile`. Treat the downloaded pairing file as a temporary private capability; do not share it or paste it into a public issue.

New pairings have no time expiry or ten-file cutoff. The watcher holds handles to this checkout's owned backend and private UI processes and exits when either stops. Foliolet's Stop action also stops the managed watcher. After a successful background connection, subsequent Foliolet launches resume that pairing; **Stop watching** revokes it and prevents reconnection. Older timed pairings still honor their original expiry and file limit.

The watcher recursively handles newly received PDF/TXT/CSV files, completed writes and final download renames. It ignores files older than the pairing, hidden/system files, partial extensions, unsupported files, symlinks and junctions. Each file is limited to 20 MiB. It cannot prove which browser/site created a file. **Stop watching** revokes the server capability and paired observation agent; Ctrl+C also stops a foreground companion. Re-arming explicitly replaces the prior pairing. Changing the directory requires a new pairing.

The private folder list also lets you select supported files already present before pairing. Those files are imported only when selected and remain self-enrolled unless the current agent observed their exact bytes. Historical session receipts are not used to populate this list. Selections are bound to the signed-in holder, current pairing and file version; if a file changes or the pairing is replaced, wait for the refreshed row and select it again. This inventory and import action are unavailable on the public receiver.

The companion retains an encrypted outbox after a disconnect or failed upload. Restart it with the same unexpired pairing to resume; it checks source bytes again, and refuses an old snapshot if the source changed after observation. Source downloads are never deleted or overwritten. Expired/revoked sessions require a new explicit pairing; use normal upload for a retained download instead of assuming an old outbox will be accepted under a new session.

**Manual fallback:** close the external tab whenever desired, select the normal file picker, name the document and upload. It works with no watcher or model. Unsupported formats retain the encrypted original and allow manual fields. Technical paths are in **Advanced**. A model/parser/OCR failure exposes Retry and manual entry; uploading never anchors or shares automatically.

## Runtime files on a different Windows machine

The exact `-RuntimeRoot` commands above were executed on this host. For a separate installation, place existing trusted portable tools at `<RuntimeRoot>\.local-tools\postgres\bin`, `<RuntimeRoot>\.local-tools\ocr\Library\bin` and `<RuntimeRoot>\.local-tools\ocr\share\tessdata`. Install this repository's locked Node dependencies in that runtime root with `npm ci` and `npm ci --prefix spring-boot-service`; alternatively use this new worktree as RuntimeRoot. `tools/setup-local-postgres.ps1` can explicitly install its pinned, hash-checked portable PostgreSQL package into this worktree if absent. It does not initialize a database until the demo launcher runs.

Tesseract and a cloud-disabled local Ollama model are prerequisites for OCR/AI, not for manual enrollment. This assignment reused the existing packages; a fresh download/install of those runtimes on another computer was **not performed**. The older `setup-foli-runtime.py` is intentionally restricted to `cf`: do not switch branches, edit that guard or run it in another checkout for this feature. No global PATH changes or heavyweight vision installation are necessary.

## Reproduce the tests

Use the exact commands in [the test report](DIGILOCKER_ASSISTED_INTAKE_TESTS.md). Run the live API, fault and browser scripts sequentially; they use disposable synthetic accounts and this dedicated cluster, preserve their state, and retain local logs under `.local-data`. The fault suite launches only its own additional Java service on 8098 and leaves the shared real Ollama untouched. It requires 8098 and the local test-double port to be free.

## One-minute demonstration

This is a script for a consenting operator with their own issued document. A real issued PDF, DigiLocker login/download and physical NFC were unavailable during this assignment; those parts are **NOT TESTED**.

* **0–10s:** Open Enroll, show the official DigiLocker tab, choose Issued Documents and download into the explicitly paired folder. Show **Watcher connected** locally. Authentication time is outside the one-minute target.
* **10–25s:** Show **File received → Reading document → Review facts**. Point to **Possible DigiLocker document (unverified)** only if an indicator was actually found, the independent **First-seen tracked** label, and **Issuer not verified**.
* **25–40s:** In a marksheet containing literal `Math: 90`, open its source page. Show the suggested decimal 90 and warnings; edit to 95 to show the modified preview. Revert to the original proposal for unchanged lineage, or confirm the edited value to show the server's modification count.
* **40–60s:** Explicitly confirm and anchor; share only Math, open the recipient proof and verify it. An existing NFC tag may discover that same recipient link; physical tag read/write is outside the tested evidence.

For a reproducible local rehearsal without real credentials, run `tools/make-intake-fixtures.py` with the existing Node runtime on `NODE_PATH`, then place its clearly labeled **synthetic** `both.pdf` into the armed folder after pairing. The browser/API tests exercise this synthetic flow. A copied logo or synthetic official-origin QR cannot establish government authenticity. Generic QR yields no DigiLocker-specific positive. Real issuer verification would require an authorized source protocol or supported signed payload plus independently provisioned issuer trust, scope, expiry/revocation and audit controls; none is represented by this feature's badges.
