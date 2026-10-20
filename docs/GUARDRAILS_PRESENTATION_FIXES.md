# Guardrails presentation fixes — 18 October 2026

Implemented only in `Foliolet-askfoli-guardrails`, on `codex/askfoli-document-guardrails` based on `cbd7967`. Main and `Foliolet-frontend-redesign` were not edited, switched, merged, or restarted.

## Corrections

1. **Desktop startup:** the exact guardrails branch is now permitted. Main and unrelated branches remain rejected. Startup, ownership checks, readiness, the desktop browser URL, and watcher pairing use the validated ports saved in this checkout's `.local-data/intake-runtime.json`. Explicit ports supplied to `start-digilocker-demo.ps1` are saved before any services start, so a partial start can be recovered on the same ports. Existing default-port checkouts retain their defaults. The running guardrails manifest was populated once with its existing ports: PostgreSQL 55448, EVM 8558, API 8089, UI 8018, receiver 8001, control 8002. Its previous manifest is retained in the verification directory. Startup also reuses the retained runtime's Node packages instead of unnecessarily installing another copy.
2. **Folder watcher:** pairing must match the configured numeric loopback API exactly, rather than hardcoded port 8088. The existing checkout/PID/start-time checks remain, with listener ownership checked before launching. Wrong ports, hostname alternatives, remote origins, and extra paths are rejected before companion state is written.
3. **Fact-row evidence:** generated source evidence has an explicit DOM marker. Adding a manual row, clearing the last row, or reusing a row for a new scan clears both the evidence and scan note. The Advanced field-path editor and the original row's evidence are preserved when adding another row.
4. **Shutdown:** the stop script now stops the detached receiver and Cloudflare through their authenticated, checkout-specific control API and waits for the receiver/control ports to close. It refuses a mismatched control endpoint instead of killing a process by port. An already-stopped receiver is handled without an error. Existing application and PostgreSQL ownership checks remain.

No AskFoli prompt or grounding rules were loosened by these changes.

## Fresh verification

Evidence is retained under [`.local-data/presentation-fixes-20261018`](../.local-data/presentation-fixes-20261018/).

| Check | Result |
| --- | --- |
| Launcher configuration regressions | 6 test methods, with scenarios exercised on PowerShell 5.1 and 7: defaults, saved custom ports, canonical numeric ports, legacy configuration, foreign checkout rejection, invalid/duplicate ports, and main/unrelated branch rejection |
| Actual watcher launcher | 4 checks passed on each of PowerShell 5.1 and 7, including real authenticated connection on port 8089, server-side Stop, expired pairing rejection, and invalid endpoint rejection |
| Live launcher lifecycle | 13 checks passed: readiness, repeated start without reinstalling or replacing service PIDs, startup mutex, Stop, retained-data hashes, all configured ports closed, old supervisor and Cloudflare processes terminated, repeated Stop, foreign-port refusal, cold restart on saved ports, warm start, and a new ready public tunnel |
| Controlled browser fact editor | 8 checks passed, including new-row and last-row evidence regressions, OCR acceptance, reread/edit preservation, desktop/mobile light/dark layouts, and inert document markup |
| Real browser native/scanned PDF workflow | 7 checks passed: native fields, leading-zero IDs, source preview, reread, Add a fact without inherited evidence, scanned OCR acceptance, confirmation lineage, and desktop/mobile checks |
| Live wallet workflow | 51 checks passed against PostgreSQL, Spring, Django, and EVM, including anchoring, selective disclosure, one-time use, revocation, export, and recovery of synthetic fixtures |
| Live AskFoli | 5 cases passed: no-document guidance; cited monthly fee; refusal of “Give me script to do recursion”; cited cancellation fee; and supported notice period without answering the unrelated geography request |
| Live public HTTPS sharing | 12 checks passed: creation, landing, release, hidden-value exclusion, proof download, one-time enforcement, revoked export rejection, and private-route blocking |
| Browser chat history | 11 checks passed |
| Java backend | 164 tests: 160 passed, 4 skipped, no failures/errors |
| Django | 119 tests: 118 passed, 1 skipped, no failures |
| Node proof/verifier/QR | 24 passed |
| Watcher unit tests | 13 passed |
| OCR layout worker | 4 passed |
| Static validation | PowerShell parsing, changed Python/JavaScript syntax, and Git whitespace checks passed |

The lifecycle test used the real launcher worker in headless mode; it did not open the desktop window. Before and after Stop/cold restart, it compared hashes of retained originals, encryption/signing keys, and registry pins. These were unchanged. Synthetic test accounts and documents remain isolated from existing personal records.

## Retained failed attempts and limits

The first new browser regression assertion inspected visible text inside a collapsed details element; it was corrected to inspect the element's text content. The initial isolated PowerShell test invocation omitted process-local ExecutionPolicy Bypass; that harness invocation was corrected. Neither required weakening application behavior. Original logs remain alongside the passing reruns.

An initial parallel run of the document-heavy live suites exceeded the reader's single-document capacity: four AskFoli jobs explicitly returned `BUSY`, and the concurrent browser source-preview assertion failed. The live wallet suite completed all 51 checks. Native/scanned PDF, AskFoli, and public-sharing probes were then run sequentially and all passed. This does not establish simultaneous multi-document capacity; that pre-existing limit remains.

Four Java platform-specific permission/symlink tests and one Django symlink test remain skipped on Windows. Docker deployment, physical-phone QR/NFC interaction, and real DigiLocker provider authentication were not part of this fix verification. The five passing model cases do not establish general numerical accuracy or eliminate the historical summary-quality limitation recorded in the audit.

The successful restart replaced the temporary Cloudflare hostname. New disclosure links should be created from the running app; links on the former quick-tunnel hostname are no longer served. The private app remains at `http://127.0.0.1:8018/`, with the local model on 11444 and public receiver/control on 8001/8002.

No merge or push was performed. Main stayed at `76aca8fb65dd11e0b7e22078b2a231726ee99b32`; frontend-redesign stayed at `391593c9bdbe8cd7963bc1b0431e725baab67658`, both with clean Git status. Changes and regression tests remain in the guardrails checkout for review.
