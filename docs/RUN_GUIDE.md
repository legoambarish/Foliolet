# Run Foliolet locally

Run commands from the repository root unless a directory is shown. Prerequisites: Windows PowerShell, Java 17+, Node/npm, Python 3.12+ and either PostgreSQL or working Docker. Maven is provided by the wrapper. This guide uses loopback-only development services and an ignored local development relay key. Do not fund that key outside the isolated local chain.

## Install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r django-service/requirements.txt -r tools/requirements-dev.txt
npm ci
npm --prefix spring-boot-service ci
npm run contracts:build
npm run assets:build
```

Committed ABI/bytecode and local browser assets allow ordinary startup without recompilation. The compiler is pinned to Solidity 0.8.19; it builds the new registry and preserves the inherited compiled registry. `npm ci` rather than an unpinned global Ganache is recommended. Installed Node may print an optional native µWS warning; Ganache's JavaScript fallback was successfully tested.

## Choose one PostgreSQL route

**Portable Windows route, tested on this machine:**

```powershell
.\tools\setup-local-postgres.ps1
.\tools\start-postgres.ps1
```

The optional setup downloads checksum-pinned PostgreSQL 17.6 binaries from Maven Central into `.local-tools/postgres`. Startup initializes a separate cluster under `.local-data/postgres`, binds only `127.0.0.1:55432` and creates `wallet_dev` for user `wallet`. Trust authentication is restricted to this local development cluster. An existing compatible binary directory can be supplied using `-PostgresBin`. Do not point this initializer at an existing user cluster.

**Docker alternative (Compose configuration supplied; Docker daemon was unavailable during this run):**

Copy `.env.example` to `.env`, replace its placeholder password, then:

```powershell
docker compose up -d postgres
# In the terminal that will start Spring:
$env:SPRING_DATASOURCE_PASSWORD = 'the-password-you-put-in-.env'
```

Compose exposes the same loopback port 55432. Do not run both PostgreSQL routes on that port. PowerShell scripts do not source `.env`; set the backend environment variable explicitly. If using an existing server, create a separate development database and configure `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME` and `SPRING_DATASOURCE_PASSWORD`. Never repoint a production database without reviewing schema migration behavior.

## Start services in separate terminals

```powershell
# Terminal 1: persistent local EVM, chain ID 1337
npm run evm
```

```powershell
# Terminal 2: Spring Boot + Web3j
.\tools\start-backend.ps1
```

```powershell
# Terminal 3: Django, migrations and localhost server
.\tools\start-frontend.ps1
```

Open `http://localhost:8000/`. Use `/register/` to create a HOLDER account (username 3–60 allowed ASCII characters; password at least 12 characters, at most 72 UTF-8 bytes). No seeded privileged account is required. All wallet data comes from real Spring endpoints.

Spring deploys/reuses **both** real contracts. Contract addresses persist under `.local-data/chain`; Ganache data under `.local-data/evm`. Keep PostgreSQL, chain data, address files, vault key, Django key and encrypted wallet files together when restarting/backing up. Removing/resetting EVM state alone breaks existing anchors; startup fails when persisted contracts are missing rather than silently declaring old proofs valid.

The EVM launcher generates `.local-data/development-relay.key` on first use. It prints only the operator address; Spring's launcher reads the key locally unless `BLOCKCHAIN_PRIVATE_KEY` is supplied. Keep that ignored key with the EVM state. If an existing chain lacks the key, restore its original key rather than generate another identity. Never use this development identity on a funded public network. Test signers are generated in memory and are unrelated to the local deployment.

### Configuration

Provision independent verifier pins **before the demo**, separately from the proof and Spring HTTP service. Create `.local-data/trusted-deployment.json` (or set `WALLET_TRUST_FILE` to an absolute path) containing:

```json
{"contract":"0xYOUR_TRUSTED_REGISTRY","operator":"0xYOUR_TRUSTED_OPERATOR","chainId":1337}
```

Replace both placeholders with validated nonzero 20-byte addresses from the operator's deployment record and check the registry directly using a trusted RPC. The local demo uses a manually provisioned snapshot of the retained registry deployment plus the operator/chain identity configured for the local EVM. Do not populate it from `/api/public/network` or a downloaded bundle. Do not automatically refresh pins when a service reports a different identity. Restart Django after changing the file. Missing/malformed pins leave independent acceptance unavailable; the service badge alone is not an independent check. The file is local/ignored and must be independently provisioned on another checkout.

The session migration automatically purges legacy plaintext suggestion copies, including expired session rows. It preserves other session fields and vault originals. This is not secure erasure of old database pages/backups. Backend startup adds `users_username_unique`; conflicting existing usernames must be resolved by an operator without automatically merging accounts. This checkout had no retained duplicates, and the installed constraint was tested directly in PostgreSQL.

| Setting | Purpose / local default |
|---|---|
| `PRODUCT_LABEL` | Public UI label, `Foliolet` |
| `SPRING_BOOT_API_BASE_URL` | Django bridge, `http://localhost:8080` |
| `PUBLIC_EVM_RPC_URL` | Browser direct RPC, `http://127.0.0.1:8545` |
| `WALLET_TRUST_FILE` | Separately provisioned JSON pins, default `.local-data/trusted-deployment.json`; no Spring discovery fallback |
| `BLOCKCHAIN_RPC_URL`, `BLOCKCHAIN_CHAIN_ID` | Spring RPC / expected chain, loopback / 1337 |
| `BLOCKCHAIN_PRIVATE_KEY` | Required funded relay; start script reads the ignored local EVM key if unset |
| `BLOCKCHAIN_CONTRACT_ADDRESS`, `SELECTIVE_CONTRACT_ADDRESS` | Optional explicit identities; otherwise persist deployments |
| `WALLET_ENCRYPTION_KEY` | Base64 32-byte key; local default generates `.local-data/vault.key` |
| `WALLET_DATA_DIR` | Private storage/key/address directory, `../.local-data` relative to Spring working directory |
| `WALLET_SHARE_BASE_URL` | Link origin, `http://localhost:8000` |
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Session secret, local debug/hosts |
| `ENABLE_LEGACY_UI` | Default false; true exposes retained `/legacy/` screens |

Existing ignored `spring-boot-service/src/main/resources/application.properties` takes precedence over YAML. Inspect it rather than overwrite an existing installation. Default scripts intentionally start from the service directories so storage paths are stable. A bare jar must also run from `spring-boot-service` or use an absolute `WALLET_DATA_DIR`.

## Five-minute selective-disclosure demo

1. Sign up/sign in. Enroll `docs/demo-marksheet.txt` as Education, using a normal display name.
2. Review five suggested facts against the original. Confirm the review checkbox. The platform adds the sixth fact, **CGPA at least 8.5 = true**. Its derivation limitation is visible.
3. Click **Anchor commitment**. Show the Merkle root, real transaction, contract and chain ID. No values or original bytes are in the registry.
4. Click **Share a proof**, select only the threshold boolean, enter intended verifier/purpose, choose expiry and optionally one-time release. Preview shows **1 fact disclosed, 5 private**.
5. Copy the private link or scan its local QR. The public GET page reveals no facts. A verifier explicitly presses **Open disclosed facts**; no account is needed. They see `true`, source assurance and signed context, without exact CGPA, name, birth date or institution.
6. Click **Check proof and chain**. Compare registry/operator/chain pins against a trusted address outside the link. This browser recomputes the proof/signature and reads the EVM directly. The service release result and independent result are distinct.
7. Download the JSON bundle. Run the separate verifier:

```powershell
node spring-boot-service/scripts/verify-proof.cjs C:/absolute/path/proof.json --contract 0xYOUR_TRUSTED_REGISTRY --operator 0xYOUR_TRUSTED_OPERATOR --chain-id 1337 --rpc http://127.0.0.1:8545
```

Export downloads only the bundle already released to that browser session and rechecks current policy without consuming a one-time link again. The Node tool does not need Spring, holder credentials or the original file. It reports that service-link policy was not checked; query the live grant status separately for revocation policy. A retained bundle remains copyable.

8. Demonstrate a changed JSON value failing proof verification; revoke a link (new release fails), create/anchor a new version (old credential becomes SUPERSEDED), and revoke a credential (direct latest-chain check fails). The automated live suite covers these using disposable records.

### First-seen demo

Open Integrity, pair an agent and save its ID/secret once into `.local-data/agent.json` **outside** the watched folder:

```json
{"agentId":"YOUR-UUID","secret":"0xYOUR-32-BYTE-SECRET","apiUrl":"http://localhost:8080"}
```

Create an intake directory and place a harmless file in it. Run:

```powershell
.\.venv\Scripts\python.exe tools/local-watcher/watch.py C:/absolute/path/intake --config .local-data/agent.json
```

The recursive watcher samples stable files and sends signed, ordered fingerprints. Enroll the same unchanged bytes and choose their received observation. Assurance becomes **First-seen tracked**, explicitly sampled and holder-controlled. Change the file while the agent runs, then enroll with its history: continuity fails and assurance remains self-enrolled. State is durable beside the configuration; use `--once` for a single scan. Keep configuration/state out of the watched tree and Git. Pending reports older than 24 hours need a new pairing/recovery; deleting the state of an existing agent cannot reset the server sequence.

## Tests

```powershell
Push-Location spring-boot-service
.\mvnw.cmd -B package
Pop-Location
npm run test:contracts
npm run test:verifier
Push-Location django-service
..\.venv\Scripts\python.exe manage.py test dashboard
..\.venv\Scripts\python.exe manage.py check
Pop-Location
# Requires all live services and creates harmless test records/files:
.\.venv\Scripts\python.exe tools/test-live-workflow.py
.\.venv\Scripts\python.exe tools/test-live-security.py
```

The workflow suite checks 51 assertions using real HTTP, PostgreSQL locking and Solidity/Web3j transactions, and preserves `.local-data/live-test-results.json`, `live-test-proof.json` and a fresh `demo-session.json`. It mutates only its own disposable grant expiry and its own encrypted test files; damage is restored in `finally`. Use an isolated local database, not an existing user's data. Unit tests use H2/mock chain only for isolated failure scenarios; contract/live tests use genuine EVM execution.

When rebuilding on Windows, stop a backend running from the executable jar first; Windows locks that jar and prevents repackaging. The default Maven-run script avoids this lock.

## Stop without deleting data

Press Ctrl+C in the EVM, backend and Django terminals. Portable PostgreSQL runs in the background:

```powershell
& .\.local-tools\postgres\bin\pg_ctl.exe -D .\.local-data\postgres -w stop
```

For Docker use `docker compose stop postgres`. Neither command deletes persisted data. Never use a volume-removal/reset operation as a normal restart. See [security limitations](SECURITY.md) before moving beyond localhost.

The additional live security suite checks registration races, strict bundle parsing, transient extraction, hidden salts, independently configured pins, tampering and custom labels. It retains `.local-data/live-security-results.json` and a fresh `security-demo-session.json`. Both live suites require separately provisioned local pins.
