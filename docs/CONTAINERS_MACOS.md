# Run the complete Foliolet stack with Docker on macOS

Install and start [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/).
Use this branch's checkout. No host Java, Python, Node, PostgreSQL or Ollama installation
is required for application startup. Allow Docker Desktop access to your checkout and
Downloads folder. Start with 8 GB assigned to Docker; CPU inference and OCR benefit
from additional memory.

The current local changes are also packaged in `.local-data/Foliolet-macos-source.zip`
on the development machine. Transfer and extract that archive on the Mac, then open a
terminal in its `Foliolet` folder. It includes the local changes that have not been
pushed to GitHub and excludes private state, keys, installed dependencies and Git
history. To rebuild it after editing source, run `python tools/package-container-source.py`.

From the repository root, run this single command:

```sh
docker compose up --build -d --wait --wait-timeout 1800
```

Open [Foliolet](http://127.0.0.1:8008/). The first build installs the pinned application
dependencies and downloads the missing `qwen3:4b-instruct` model, about 2.5 GB.
The command waits for the UI, API, local EVM, model and watcher supervisor to be ready.
Later starts reuse Docker build layers, dependency caches and the persistent model
volume. A slow first download may need a longer `--wait-timeout`; startup progress
remains available with `docker compose logs -f app ollama`.

Create your holder account, sign in, open **Enroll**, expand **Use an optional local
folder watcher**, consent and select **Enable folder intake** once. The watcher
connects automatically. No pairing file download or additional terminal command is
required. Saved pairings resume on subsequent starts. There is no session expiry:
watching lasts while Foliolet runs, until you select **Stop watching**.

Your Mac folder is **`~/Downloads/Foliolet Intake`**. Compose creates it if missing;
save finished PDF, TXT or CSV files there, including subfolders. In the UI the mounted
folder appears as `/app/imports/foliolet`. The container reads that folder without
permission to modify source files. New files import automatically; available files
appear newest first and clicking a row imports that exact document. Existing files
from before pairing remain available to import by clicking their rows.
If the folder is reported unavailable, check Docker Desktop file sharing and the
folder/files' read permissions for the container user.

## What the command starts

| Component | Runtime and access |
| --- | --- |
| Spring Boot / Spring AI | Java 17, private loopback API on 8088 |
| Django | Waitress on private 8008; Nginx serves the host UI on `127.0.0.1:8008` |
| EVM | Persistent Ganache chain 1337; browser RPC on `127.0.0.1:8548` |
| PostgreSQL | Internal container network only, no host database port |
| Ollama | Local Qwen inference, cloud disabled, private loopback 11434 |
| OCR | Tesseract English and checksum-checked RapidOCR/ONNX models |
| Watcher | Per-holder companions, process-bound lifetime, host-folder polling |
| Cloudflare | Binary included; existing receiver-only sharing starts it on demand |

The application container supervises its frameworks and companions. PostgreSQL and
Ollama have separate containers. A small network container keeps the private loopback
namespace stable when application/model processes restart. Database, Spring, model
API, receiver and control ports are not published to the host. Only the local UI and
development-chain RPC are published, on host loopback.

The same Dockerfile targets native `linux/arm64` and `linux/amd64`, for Apple Silicon
and Intel Macs. Docker Desktop runs Linux containers; this setup uses CPU inference.
It does not provide macOS Metal GPU acceleration. See the official
[Ollama Docker instructions](https://docs.ollama.com/docker).

## Automatic configuration and persistence

No `.env` file or credentials are required. Startup generates a random database
password only when missing, starts PostgreSQL, creates/reuses the EVM relay identity,
checks the deployed registry's trust pins, migrates Django, launches the frameworks
and watcher supervisor, then pulls Qwen only if absent. All required service URLs,
credentials, model/OCR paths, private ports and browser RPC settings are injected
into the child processes automatically. A damaged retained secret or mismatched
trust pin fails startup instead of silently replacing identity.

| Persistent location | Contents |
| --- | --- |
| `foliolet_app` volume | Encrypted vault, keys, chain database, deployment pins, Django sessions and private watcher state |
| `foliolet_postgres` volume | Holder accounts and application records |
| `foliolet_secrets` volume | Generated database password, read-only to the running services |
| `foliolet_models` volume | Ollama model manifests and blobs |
| `~/Downloads/Foliolet Intake` bind mount | Your original source documents, read-only inside the app |

These are new container-specific stores. The Windows native launcher's `.local-data`,
host virtual environment, user databases and existing host Ollama cache are not
imported or changed. Docker caches its own dependencies and models. Keep all four
volumes together when backing up or moving an existing container installation.
Ordinary `stop`, `down` and subsequent `up` retain them. **Do not add `--volumes` / `-v`
to `down` for your real installation: that deletes the saved container data.**

The model is [Qwen3 4B Instruct](https://registry.ollama.com/library/qwen3:4b-instruct).
Model pulls use the registry during setup; document inference stays local with
`OLLAMA_NO_CLOUD=1`, as described in the [Ollama FAQ](https://docs.ollama.com/faq).

## Optional startup overrides

The defaults need no environment file. To use a different dedicated source folder:

```sh
FOLIOLET_INTAKE_DIR="$HOME/Documents/Foliolet Intake" docker compose up --build -d --wait --wait-timeout 1800
```

Use an absolute folder path, keep other personal downloads outside it, and continue
using `/app/imports/foliolet` in the UI. Read-only
[bind mounts](https://docs.docker.com/engine/storage/bind-mounts/) and
[health-based startup dependencies](https://docs.docker.com/compose/how-tos/startup-order/)
are declared in `compose.yaml`.

If ports 8008 or 8548 are already occupied, choose different host ports without
stopping the other application:

```sh
FOLIOLET_HTTP_PORT=18008 FOLIOLET_RPC_PORT=18548 docker compose up --build -d --wait --wait-timeout 1800
```

Then open `http://127.0.0.1:18008/`. Keep the same overrides on later `up` commands.
For a local-only sharing rehearsal, prefix the startup command with
`FOLIOLET_SHARE_MODE=local`. Default quick sharing uses the existing receiver-only
Cloudflare tunnel; it never tunnels the private UI or backend. Quick Tunnel
hostnames may change after an explicit tunnel restart.

## Status, shutdown and tunnel recovery

```sh
docker compose ps
docker compose logs -f --tail=100 app ollama
docker compose exec app python /app/docker/tunnel.py status
docker compose exec app python /app/docker/tunnel.py restart
docker compose stop
# Later, use the original one-command startup again.
```

Restarting the tunnel explicitly replaces its temporary public hostname. The tunnel
CLI wrapper injects the same configuration as application startup. Files in the
watched folder and saved wallet data survive shutdown. Watchers stop with the app;
their encrypted pending queues and pairings resume on the next start.

The older Windows/manual PostgreSQL-only route is retained in
`compose.postgres.yaml`; follow [RUN_GUIDE.md](RUN_GUIDE.md) for that route.

## Verification and current limit

Verified on the development host on 2026-10-17:

- `docker compose config --format json` resolves the complete service graph.
- Ollama 0.40.5, cloudflared 2026.10.1 and all four build/runtime base-image
  registry manifests contain both Linux ARM64 and AMD64 variants.
- An isolated npm installation resolves the locked EVM dependencies for Linux ARM64.
- The 116 Django tests finish successfully (one existing platform-specific skip).
- All 13 existing watcher tests and 12 container-runtime regression tests pass,
  including cold/warm model preparation, Linux process identity, watcher resumption,
  revocation, holder isolation and automatically injected configuration.

**Full container builds and macOS execution are not yet verified.** This development
machine's Windows Docker Desktop engine fails before creating its Linux engine pipe.
The attempted `docker compose build` fails while connecting to the daemon, before
any image build. No Docker engine cleanup or reset was performed, and the running
native Foliolet installation was not stopped.

Once Docker is running, the real-stack acceptance test is:

```sh
python3 tools/test-container-stack.py
```

This optional test requires host Python 3; ordinary application startup does not.
It allocates a unique disposable Compose project, synthetic input folder and free
ports. It builds the image, runs real Spring AI inference, pairs the automatic
watcher, checks exact-byte imports and deduplication, verifies newest-first updates,
then performs down/up to check identity, account, model-cache and watcher persistence.
It removes only its own disposable containers/volumes and retains logs under
`.local-data/foliolet-smoke-*/`. It does not select the normal `foliolet` project.
