# Foliolet desktop launcher

Double-click **Foliolet** on the Windows desktop. A small progress window starts the local database, proof chain, document assistant and web services, then opens **http://127.0.0.1:8008/** in your default browser. No terminals or commands are required.

The same entry point is **Foliolet.vbs** at the root of this feature checkout. It uses Windows' built-in PowerShell and Forms, so no desktop framework or extra launcher runtime is installed. The desktop shortcut is generated for the current checkout; if the folder is moved, use `Foliolet.vbs` in its new location.

The window has **Open Foliolet**, **Stop Foliolet** and **Close** buttons. Closing the window leaves the services running. Stop preserves documents, databases, chain state, keys, model files and settings. Start again resumes that saved state. Repeated clicks reuse the same running instance. Closing the window during startup also leaves startup running; reopening attaches to its progress.

Startup finds the retained PostgreSQL/OCR/Node tools in this checkout or the sibling `Foliolet-testcloudflare` automatically. It creates the project Python environment and installs the project requirements if needed, checks Node packages, builds a missing or older Java JAR and starts the existing local Qwen model. Once prepared, ordinary launches reuse those files. Missing project packages or a Java build can need internet access on first setup; document inference stays local. The selected model is reused or copied with hash verification, never downloaded by the launcher.

This machine already has Java 17, Python 3.12, Node, Git and the portable PostgreSQL/OCR/model runtime. Installing those system prerequisites on a different computer is outside this launcher's bootstrap; missing tools produce a clear error in the progress window. It does not silently install a new system Java, download a large AI model or alter another checkout.

Services start hidden, with readiness checked before opening the browser. Only processes identified by this checkout's PID/start-time/command records and its exact PostgreSQL data directory can be recovered or stopped. An occupied port belonging to another application is refused. Local ports remain `8008`, `8088`, `8548`, `55438`, with an optional owned CPU model on `11444`; a healthy existing cloud-disabled model on `11434` can be reused. Nothing is exposed through a tunnel.

Use **View startup details** if startup fails. Per-step stdout/stderr and status records live under `.local-data/desktop-*`; your originals and keys must be retained. Folder watching still requires the normal explicit pairing/consent inside Foliolet.

Developer entry points (ordinary users do not need these):

```powershell
./tools/install-foliolet-shortcut.ps1
./tools/start-foliolet.ps1
./tools/start-foliolet.ps1 -CheckOnly
./tools/start-foliolet.ps1 -Stop
```

The original [assisted-intake setup and demonstration](DIGILOCKER_ASSISTED_INTAKE_RUNBOOK.md) and [acceptance matrix](DIGILOCKER_ASSISTED_INTAKE_TESTS.md) still apply.

## Measured Windows verification, 16 October 2026

| Check | Observed result |
| --- | --- |
| Native startup/stop/GUI acceptance | PASS: 8 checks using built-in Windows PowerShell 5.1 |
| Concurrent status I/O | PASS: 101 atomic updates consumed by a separate real PowerShell process |
| Default browser opening | PASS: the real launch target opened Chrome at `/login/`; visible Sign in page checked |
| Desktop shortcut | Created; exact target, arguments and working directory inspected |
| Existing Django suite | PASS: 72 |
| Existing independent proof/UI Node suite | PASS: 22 |
| Affected PowerShell syntax | PASS: all six scripts |
| Normal desktop environment | PASS: Java, Python, Node and Git resolved using the saved Windows machine/user PATH, without Codex additions |

The eight startup checks cover owned Django's child Python process, PostgreSQL's forward-slash command path, repeated start with unchanged PIDs, concurrent start refusal, Stop with unchanged encrypted originals/backups/keys/registry pins, foreign occupied-port refusal, a real cold start through the Forms window, a warm GUI launch and actual HTTP readiness. The first row's eight check names group the related readiness assertions in the test source; the [sanitized evidence](desktop-launcher-evidence.json) preserves the executed names.

Corrected failures included Windows PowerShell's JSON array enumeration, inherited PowerShell 7 module paths, fast native-child exit-code handling and a status-file sharing race. The status reader now permits atomic replacement and retries transient contention; the UI also allows a final process status to arrive before treating exit as failure. An initial standalone Node command lacked the existing runtime's `NODE_PATH`; rerunning with the documented runtime paths passed all 22 tests. No product authorization was relaxed.

Automated activation of the `.lnk` in a combined shortcut/document-check command was blocked by automatic approval review with the reason “blocked by policy.” The retained-document credential check in that command was not performed. The shortcut's exact PowerShell target was subsequently inspected and executed directly, and its browser-open result was verified in Chrome. No claim is made that automation clicked the desktop icon itself.

Raw logs/captures remain in ignored `.local-data/desktop-tests` and `.local-data/desktop-*`. The existing 100-test Java result belongs to the preceding intake implementation; Java production code was unchanged for this launcher and that suite was not rerun or relabeled. Fresh system-prerequisite installation on a second PC remains untested.

```powershell
# Full acceptance intentionally stops/restarts this checkout's saved local demo.
./.venv/Scripts/python.exe tools/test-foliolet-desktop.py
./.venv/Scripts/python.exe tools/test-foliolet-desktop.py --status-io-only
```
