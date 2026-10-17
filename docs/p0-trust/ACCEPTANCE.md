# Acceptance and executed evidence

All examples use disposable local state and fictional facts. The supplied reference image stays local. Counts describe executed checks, not the number of possible production scenarios. Raw logs and private proofs are ignored under `.local-data/p0`; sanitized metrics are committed separately.

## Executed suites

| Gate | Result | Scope |
|---|---|---|
| Maven package | 142 tests, 0 failures, 0 errors, 4 existing skips; package successful | Java security, reader, layout, canonicalization, cryptography, source authorization, cache, cloud gates/fallback, signatures and intake integration |
| Django dashboard | 117 tests, 0 failures, 1 existing skip | Includes strict new-extension validation, private/public boundaries and recipient rendering |
| Node verifier/UI | 23/23 | Old/new envelope domains, selected metadata, alteration/strip/null/extra field rejection and independent-verifier UI |
| Solidity integration | Passed | Real isolated Ganache: registry authorization, immutable roots, unsupported assurance, atomic supersession, revocation and seven Merkle shapes |
| Live wallet HTTP | 51/51 | PostgreSQL, encrypted vault, EVM, Django CSRF release/export, single-use race, expiry, revocation, versions, actual watcher and legacy compatibility |
| Live intake HTTP | 46/46 | Actual watcher, PDFBox/Tesseract, baseline comparison/retry, PDFs, malformed/protected/unsupported files, existing local chat and review |
| Sender Edge browser | 11/11 | Actual pairing/stop, upload, source preview, deliberate review-required acceptance, edit/confirmation, desktop/mobile, light/dark, no external document requests |
| P0 supplied-reference path | Passed | Supplied image embedded in fictional PDF → detection → edited fact → anchor → selected disclosure → independent verifier; 8 direct API checks and 10 fresh-profile checks |
| Recipient Edge browser | 11/11 | Private live UI and actual transient Waitress restricted profile; green QR/logo, edited fact, unverified issuer, desktop/mobile overflow and hidden holder routes |
| Actual Gemini adapter | 2/2 fixed fictional smoke requests | General answer and grounded answer with a mechanically validated citation. This is not an authorization/tier determination. |
| Container runtime unit suite | 12/12 | Boot supervisor, model readiness and watcher lifecycle/failure controls |
| Compose configuration | Passed | `docker compose config --quiet`; actual daemon unavailable, so no container boot claim |
| Windows startup/restart | Passed | Existing guarded launcher on separate ports; guarded stop/restart retained isolated DB/keys/chain; original services preserved |

The four Java skips and one Django skip are existing environment-dependent gates; they are not counted as executed successes. Existing live script assumptions about watcher lifetime limits and UI review-required fields were corrected to current main behavior, without removing their checks. A 429 from the real bounded reader is retried at one-second intervals rather than weakening its guard.

## Requested scenario matrix

| # | Scenario | Evidence and expected outcome |
|---|---|---|
| 1 | Complete logo + structured QR | Supplied reference in actual PDF passes both separate backend checks; live private/restricted recipients and browsers show green detection only. |
| 2 | Observed array format | Strict parser/decoder unit test plus supplied live QR; raw contents absent from recipients. |
| 3 | Verification URL | `IntakeIndicatorsTest` and live `qr-only.pdf`/`both.pdf`; exact origin only, never followed. |
| 4 | Unrelated QR | Unit URL boundary vectors and live unrelated QR PDF; no associated positive. |
| 5 | Forged/malformed profile | Unknown/malformed/trailing/type variants rejected in unit test; a copied/fabricated valid profile may be detected, never authenticated. |
| 6 | Copied logo only | Live `logo-only.pdf`, no issuer upgrade. |
| 7 | Qualifying QR without logo | Live `qr-only.pdf`, independent detection. |
| 8 | Dense low-resolution QR | Actual supplied image and its PDF rendering experiment: 130 DPI fails, 200 DPI passes. |
| 9 | Rotation | Deterministic Java quarter-turn QR and branding fixtures. Arbitrary skew was not certified. |
| 10 | Scanned/uncertain text | Live scanned and hybrid fixtures; source-aligned OCR fields retain support/review quality; sender requires deliberate acceptance. |
| 11 | Manual upload | Live supplied-reference PDF: import NOT_APPLICABLE, issuer UNVERIFIED despite QR/logo PASSED. |
| 12 | Watcher import | Actual recursive companion heartbeat, scoped observation and stable-file import; existing first-seen assurance retained. |
| 13 | Interrupted/failed import | Live partial download ignored; corrupt/protected/unsupported bytes retained with fallback; Java capability tests cover forged/mismatched receipt rejection. |
| 14 | Inconclusive inspection | Java budget/OCR gaps and no-qualified-result states remain inconclusive/not checked, never false issuer or absence success. |
| 15 | Unsigned PDF | `P0SignatureTest` and live supplied PDF: NOT_APPLICABLE. |
| 16 | Valid untrusted self-signed PDF | Generated Java fixture: integrity PASSED; issuer stays UNVERIFIED by metadata/signing policy. This particular signature fixture was not separately browser-rehearsed. |
| 17 | Tampered signed PDF | Generated Java signature fixture: FAILED. No issuer-trust claim. |
| 18 | Unchanged suggestions | Live canonical confirmation; modified stamp quiet. Selected unchanged field unit test. |
| 19 | Edited/added/removed | Live edit/add/remove counts; selected edited fact signed and displayed in both actual recipient browsers. Hidden removed history is not disclosed. |
| 20 | Reordered equivalent | Live reversal of suggestion order remains unchanged; Java canonical label/type/value tests. |
| 21 | No baseline | Manual confirmation during reading and no-model/manual fallback Java tests; no late baseline silently acquired. |
| 22 | Stale source | Source hash/version/access invalidation and encrypted tamper tests; signed metadata refuses to call mismatched source unchanged. |
| 23 | Recipient states | Actual private/restricted profile CSRF release, session-bound export, independent JS and both desktop/mobile browsers. |
| 24 | Altered metadata | Real API rejects QR/lineage changes and stripping; Node covers null, extra fields, wrong index, issuer upgrade and schema; old signed envelope tests pass. |
| 25 | Reload/retry/restart | Live immutable-baseline retry, repeat release, guarded app restart with retained state, and cache lifecycle tests. Cache intentionally clears on restart. |

Every positive stamp has a specific server condition and corresponding regression coverage. The matrix is layered coverage, not a claim that every fixture was exercised through every browser and deployment environment. A real Cloudflare tunnel was not opened. No new routes or Foli assets were added to the public receiver.

## Negative evidence and repair history

- Original supplied image: no QR decode and weak logo, three trials. Final image: both detected, three trials.
- First embedded-PDF run: branding passed but QR inconclusive. Offline PDFBox 130/200/260/285-DPI experiment isolated interpolation loss; final 200-DPI live PDF passed.
- First recipient schema test correctly rejected the unknown signed extension. Django strict validation was extended; legacy Java JSON migration was also explicitly tested rather than disabling strict parsing.
- First packaging attempt while the test API was running failed on Windows JAR locking. The guarded stop/build/start sequence succeeded. Test scripts and runbook now explain this requirement.
- Custom process commands were rejected by automatic approval review with a generic policy reason. The repository's guarded ownership/start-time-checking launcher completed the restart safely.
- Smaller local context experiment did not improve warm speed and was discarded. Extraction inspection adds cost; no artificial extraction speedup is reported.
- Gemini Flash returned four HTTP 429s; they remain failed trials. Flash Lite returned two rubric misses despite valid JSON. Application-level validation is still required.

Use `RUNBOOK.md` for commands. `METRICS.json` contains only sanitized measurements and test outcomes; it excludes bearer links, account credentials, original source contents, QR payloads and raw QR hashes.
