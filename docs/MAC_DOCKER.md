# Foliolet on macOS with Docker

This implementation lives on `codex/macos-docker`, branched from
`feature/digilocker-assisted-intake` at `db55c2c6c1209e567713fa9ab08c5441bd55bc86`.
It uses the existing Spring/Django wallet, Ganache EVM, PDFBox, Tesseract,
compact RapidOCR fallback, Ollama and recursive intake companion.

## Start everything

From this checkout on an Intel or Apple Silicon Mac:

```bash
./foliolet up
```

You can also double-click **Foliolet.command** in Finder. To obtain this branch
on another Mac, clone with
`git clone --branch codex/macos-docker --single-branch https://github.com/legoambarish/Foliolet.git`
and enter the resulting `Foliolet` folder first.

The command downloads and installs Docker Desktop into `~/Applications` if
Docker is missing, starts Docker Desktop, builds the application with its
regression tests, starts every service, downloads the missing Qwen model,
initializes retained local keys and independent deployment pins, and opens
**http://127.0.0.1:8008/** after health checks pass. No host Java, Node, Python,
Maven, PostgreSQL, Tesseract or Ollama installation is needed. The script works
with macOS's built-in Bash 3.2. A clone retains its executable bit; for an archive
that strips permissions use `bash foliolet up`.

Docker Desktop's first launch can require licence acceptance, administrator
permissions or macOS privacy/file-sharing permission. The launcher cannot grant
those permissions itself. Open Docker Desktop if its startup screen needs
attention, then rerun the same command. An existing Docker installation is kept.
See [Docker's supported macOS versions and requirements](https://docs.docker.com/desktop/setup/install/mac-install/).

Allow approximately **10 GB of Docker memory and 20 GB of free disk** for a
comfortable first build, model cache and documents. These are provisioning
recommendations, not a measured minimum. The local text model package is about
2.5 GB; the pinned RapidOCR model files total 31,749,509 bytes. Mac Docker inference
uses CPU; this setup does not expose Apple Metal to a Linux container. Cold model
startup and scanned PDFs take longer than native GPU inference. Dependencies and
model weights download on the first run; cached weights and named data volumes
survive subsequent builds. Actual startup is reported continuously in the terminal.

The default dedicated intake folder is:

```text
~/Downloads/Foliolet Intake
```

It is created automatically and mounted **read-only** into the production
watcher. The rest of Downloads and your home folder are not mounted. To use a
different dedicated folder, use the same setting for every command:

```bash
export FOLIOLET_INTAKE_DIR="$HOME/Documents/Foliolet Intake"
./foliolet up
```

Broad home/Downloads/Documents folders, relative paths, symlinks and remote
Docker contexts are refused. Docker Desktop must permit sharing the chosen
directory. Keep the three host ports free: `8008` (UI), `8088` (authenticated API
and scoped companion endpoint), `8548` (independent verifier's development-chain
RPC). These listen on **127.0.0.1 only**. PostgreSQL and Ollama have no host port.

## Demonstrate the complete workflow

1. Start with `./foliolet up`, register a holder account and sign in.
2. Select **Enroll a document**, expand **Use an optional local folder watcher**,
   check the ten-minute consent box and select **Enable folder intake**.
   Wait for **Watcher connected**. No terminal, JSON, certificate or field path is
   involved in enabling the included companion.
3. Select **Import from DigiLocker**. The official HTTPS website opens in a
   separate tab. Sign in there and download a PDF to the displayed intake folder
   or a nested subfolder. Foliolet never collects the portal's credentials.
4. A completed new PDF/TXT/CSV download is imported automatically (up to ten
   files/session). Existing files and browser partial downloads are ignored.
   Follow **File received · review suggested facts**.
5. Inspect the original-page evidence. Native source-supported facts populate
   the review form. OCR uncertainty stays in review cards until explicitly
   checked. Modify a value and confirm; **Facts edited since extraction** must
   appear independently of **Issuer not verified**.
6. Anchor the reviewed commitment, share only the desired fact and open the
   recipient link. Run the independent cryptographic check. Other unselected
   facts and the original file must not be disclosed.
7. Return to enrollment and select **Stop watching**. Further files in that
   folder are refused until you explicitly enable a new session. Expiry also
   revokes importing; the running watcher service itself does not imply consent.
8. Stop and restart the stack; the account, original, facts, chain commitment,
   encryption keys and trust pins should still work.

A copied logo or a QR pointing to a DigiLocker-looking URL is a provisional
format indicator. It is never government authentication. Watcher first-seen
provenance, exact AI/source lineage, commitment verification and actual issuer
verification remain distinct. Authentic issuer verification still requires the
existing separately configured trusted issuer/provider capability. There is no
live provider credential or government-login automation in this deployment.

## Manage and test

```bash
./foliolet status
./foliolet logs
./foliolet test
./foliolet down
```

`test` builds an additional test image and runs fictional-data checks against
this stack. It deliberately creates test accounts/documents and synthetic files
in your dedicated intake folder. Production watcher access remains read-only;
only the explicitly invoked test service gets write access to that folder.
Tests reuse the existing 46-check intake/AI/disclosure acceptance suite and the
12-check outage/security suite, plus managed-container consent/import checks.
Do not run acceptance against an unrelated Docker project or production vault.

`down` stops only this Compose project and **never removes named volumes**.
Avoid `docker compose down -v`, Docker factory reset or volume pruning: those
are destructive operator commands outside this launcher. Back up the full set
of this project's stopped volumes together, including `database`, `app-state`,
`db-secret`, `models`, `pairings` and `watcher-state`; keys and retained EVM state
must stay with their database/vault. `.local-data` in a Windows checkout is not
copied into images or silently migrated. Windows launchers and their data remain
separate. First-run generated passwords, vault/relay keys and session secrets
are never baked into images or committed.

If model downloading fails, inspect `./foliolet logs` and rerun `./foliolet up`.
Cached partial model downloads can resume. Model startup failure is explicit;
the UI is declared ready only when the configured model and core services are
ready. During a later model outage, source-supported/manual facts and original
uploads retain the existing fail-closed behavior. Missing OCR, malformed PDFs,
oversize inputs and modified source bytes must not silently gain supported facts.

## CI and delivery

`.github/workflows/mac-docker.yml` runs only on the new Mac branch and PRs targeting
it. It never pushes Git branches. Its gates are:

| Gate | Execution |
| --- | --- |
| Host compatibility | Native `macos-15` ARM64, `macos-15-intel`, Ubuntu: launcher lifecycle double, watcher security, Django, Node/Merkle/UI and contract tests |
| Image build | Native Linux AMD64 + ARM64: Maven unit tests, Python/Django/watchers, pinned compact OCR weights and frontend/contract builds |
| Full services | Both architectures: clean volumes, real Postgres/EVM/Ollama model download, HTTP and recursive watcher, PDFBox/Tesseract, exact source/lineage validation |
| Failure/security | Copied logos/QRs remain unverified; corrupt/unsupported/protected PDFs; refused model connection; invalid/cloud/oversize model metadata and forged proposals via an explicitly identified local test double; timeout/retry/restart; auth/CSRF/ownership; selective-disclosure proof tampering |
| Browser | Real Chromium: included companion consent/Stop, manual upload, mobile themes, exact evidence, OCR review/edits, anchoring, one-fact disclosure and independent chain verification |
| Persistence | Compose down/up followed by account/vault/hash/key/pin/chain verification |
| Delivery | Only tested architecture images are uploaded to GHCR; the multi-platform manifest is promoted only after **all** host and container gates pass |

GitHub-hosted macOS ARM64 runners do not support nested virtualization for this
Docker acceptance workload. The full image/runtime gates therefore run on
native Linux architectures used by Docker Desktop, while the launcher and
companion also run on native macOS. This is **not** a claim that a physical Mac's
Docker Desktop/file-sharing permissions were tested.
[GitHub runner limitations](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

The successful delivery run records the immutable multi-platform image digest.
For an existing checkout, deploy that tested image without rebuilding:

```bash
FOLIOLET_IMAGE=ghcr.io/legoambarish/foliolet/mac-product@sha256:THE_DIGEST ./foliolet deploy
```

Use the real 64-character digest from the successful pipeline. This command
refuses mutable tags. GHCR may require `docker login ghcr.io` if the repository
operator keeps package visibility private. The default source-build command
does not require registry access.

For actual Mac continuous deployment/acceptance, register a **trusted, dedicated**
GitHub Actions self-hosted Mac runner with label `foliolet-docker` and Docker
Desktop running. Dispatch **Deploy tested image to Mac Docker Desktop** on
`codex/macos-docker` with the tested digest. It pulls that immutable image,
waits for all services and runs the fictional-data acceptance suite. It does
not run automatically for PRs or on an arbitrary user Mac. A runner/physical
Mac is an external requirement; configuration alone is not successful deployment.

## Verification limits

Current execution results are recorded in `docs/verification/mac-docker.json`.
Do not equate checked-in CI configuration with a successful workflow. Model
metadata failure cases use an explicit local double; ordinary inference uses
the real local Qwen model. Real DigiLocker accounts/documents, physical NFC,
institutional issuer onboarding and Mac privacy dialogs require separate
operator/hardware checks and are never relabeled as verified here.
