# Local demonstration runbook

All actors are simulated. Use only fake documents, public test identities and zero-value local-chain funds. No service was deployed or tunneled during implementation.

From PowerShell in the repository:

```powershell
./tools/start-bridge-demo.ps1
./tools/rehearse-bridge.ps1 -ProveOffline
```

The first command builds Spring and starts isolated PostgreSQL, persistent chain, seed, Spring, private Django and independent reader. It does not start the public surface or download models. The second rehearses both credential templates, approval execution and imports with AI stopped, then demonstrates app-independent reading and fail-UNKNOWN when the chain stops. Logs and private test captures live under ignored `.bridge-data`.

Open http://127.0.0.1:8000/bridge/. Every demo account uses `Foliolet-Demo-2026!`: governance, university, employer, rogue, holder-a, holder-b, internship-verifier and tenant-verifier. Sign out between roles or use separate browser profiles. Create a holder browser key and export its encrypted backup. Losing the key prevents signing; neither the server nor a downloaded evidence package can recover it.

## Beat 1: real authority and minimum disclosure

1. Holder-a: Generate browser key, enter a backup password, Export encrypted key. Retain this file locally.
2. University: choose `demo/marksheet.txt`, review the explicitly fake values, confirm and anchor for holder-a. The issuer confirms the CGPA threshold; this is not a hidden-number proof.
3. Internship-verifier: sign a request with a clear purpose and holder-a. The default request asks only for enrollment and CGPA at least 8.5.
4. Holder-a: refresh the inbox. Review the request or prepare a bounded plan in the assistant. Inspect the exact facts, named recipient, purpose, deadline, nonce, one opening, retention and zero new chain transactions. Click Approve and sign. Save the evidence package.
5. Internship-verifier: load that package, check and save its signed decision. PASS means compatibility with the explicit test policy. Source factual truth remains UNKNOWN.

## Beat 2: converter refusal and lifecycle

Governance: inspect issuer scope and current read block. Run the rogue scenario, which submits a real unauthorized anchor transaction and displays the refusal. No file conversion can grant university authority.

Save a PASS decision before revoking. University revokes its credential. Verify the saved bundle again: current reliance becomes FAIL. Load the old signed decision into the independent reader, select historical reproduction and verify at the recorded block: the prior acceptance remains reproducible. Suspension and reinstatement have the same distinction; revocation is irreversible. A decision retry returns the saved decision, while current reliance is checked separately.

## Beat 3: independent reader

Open http://127.0.0.1:8090/. Upload the saved package and `.bridge-data/config/bridge-pins.json`, provisioned separately from the package. Optionally load its signed decision for historical mode. Stop managed Spring/Django and Ollama: the reader still evaluates using direct RPC and its own local trust pins. If RPC also stops, current status becomes UNKNOWN. The rehearsal script performs and records this sequence, then restores the services.

## Agent and import addenda

Optional AI: `./tools/start-bridge-demo.ps1 -SkipBuild -WithAI`, then run `./.venv/Scripts/python.exe tools/warm-models.py` after downloading the documented local models. Exact source search and manual approval continue without AI. Natural language prepares a proposal; it never issues, approves or shares without the holder signature.

Holder import: choose MOCK, simulate authorization, consent to fetch, inspect SELF_ASSERTED, and confirm reviewed fields. The import does not issue a native credential. Uploaded XML is limited to 128 KiB. Unsupported schema/signature authority stays UNKNOWN. Setu is disabled without authorized credentials and a stable callback URL.

Restricted local public preview: `./tools/start-bridge-demo.ps1 -SkipBuild -WithPublicPreview` manages port 8001, or `./tools/start-public-demo.ps1` runs it in the current terminal. `/discover/`, `/verify/`, and bounded share/status routes are available; `/admin/` and private APIs return 404. No public tunnel starts automatically.

## Reset and fallback

`./tools/reset-bridge-demo.ps1 -Launch` stops managed processes and archives only isolated demo state. It preserves models, captures and the original wallet data. Never use it while retaining references to current-chain receipts for a live demonstration: those receipts belong to the archived chain. Create new artifacts after reset. Docker reset `docker compose down -v` removes only this Compose project's demo volumes.

If AI is cold or unavailable, use manual review or deterministic plan preparation. If internet fails, local native functions continue once dependencies and models are cached. If the chain is unavailable, show UNKNOWN honestly; play the labeled backup demonstration script rather than presenting a recording as live verification.
