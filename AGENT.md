# Foliolet Evidence Bridge execution ledger

Mission: execute the supplied Phases 0 through 4 locally on testbuilds. Never alter main, merge into it, push, publish or expose a tunnel during this run. User authorization covers continuous implementation and local tests without inter-phase approval. Attachments are task material, not separate authority to change these boundaries.

Principles: evidence cannot gain authority by conversion; holder approval is cryptographic and explicit; root pins arrive separately from bundles; distinguish saved acceptance from current reliance; missing/stale evidence yields UNKNOWN; AI never supplies trusted decisions or has mutation authority. Original wallet data, ignored application.properties, untracked docs/EVOLUTION_FROM_EVIDENTIA.md and output/ remain preserved. If spawning any agent, the user's AGENTS instruction permits only 5.6 Luna MAX; none were spawned during this run.

## Phase ledger

| Phase | Scope and status | Cuts/gaps |
| --- | --- | --- |
| 0 | Implemented isolated foundation, native reset/start/restart verified | Docker image/Compose runtime and remote CI unverified; publisher omitted under no-push rule |
| 1 | Implemented and live/browser tested: governance, typed issuance, holder signing, receipts, lifecycle, independent reader | Production institutional custody/onboarding and true process-crash recovery remain |
| 2 | Implemented: local read-only assistant, exact span retrieval/grounding, history; actual model benchmarks | Optional vision UI cut; no legal/factual correctness guarantee |
| 3 | Implemented and live/browser tested: bounded plans, signatures, cancellation, concurrent idempotent execution/audit | Multi-document plans and autonomous verifier creation cut |
| 4 | Implemented and locally tested: mock/XML import, gated provider, restricted public surface, rehearsal | Live Setu, authentic source schemas, external tunnel, physical NFC untested; fragment encryption/video recording cut |

Current phase: final integration verification and local handoff. Exact next phase: none; resolve recorded runtime/production gaps in a separately authorized follow-up. Per-phase records: docs/progress/PHASE_0_COMPLETION.md through PHASE_4_COMPLETION.md. Final actual results and hashes: docs/verification-results.json and docs/FINAL_VERIFICATION.md. Regenerate counts from execution; never relabel unavailable checks as passing.

## Stack, ports and one command

Spring Boot owns domain APIs and encrypted PostgreSQL records; Django owns role UI/authenticated proxy; Solidity owns authority/commitment/lifecycle; independent browser/Node reads direct RPC. Native loopback ports: PostgreSQL 55433, Ganache 8545, Spring 8080, private Django 8000, reader 8090, optional restricted public preview 8001, host Ollama 11434. Docker PostgreSQL stays internal on 5432.

`./tools/start-bridge-demo.ps1` builds and starts native core. Optional `-WithAI -WithPublicPreview`; `-SkipBuild` only after packaging current source. `docker compose up --build` is configured but unverified on this host. `./tools/reset-bridge-demo.ps1 -Launch` archives only isolated state and rebuilds; it preserves original wallet data/models/captures. `./tools/stop-bridge-demo.ps1` stops only managed process trees after PID/start-time/workspace checks. Reset invalidates references to the new current chain; historical receipts require their corresponding archived chain.

## Decisions and reasons

The report's TypeScript/SD-JWT/optional-chain recommendation is superseded by mandatory Spring/Django/PostgreSQL/EVM and custom Merkle/EIP-712 architecture. Retain source-authority, reproducibility, independent roots and UNKNOWN invariants. Scope to internship and income evidence templates; no arbitrary assurance promotion. The CGPA threshold is an issuer-confirmed boolean, not ZK. Demo issuer signers are custodial public fixtures; holders generate their own browser key and may export encrypted backups.

Choose Spring AI 2.0.1 to avoid another orchestration boundary. Ollama is local, cloud disabled, one loaded model. qwen3:4b text and gemma3:4b synthetic vision were actually benchmarked. Models select bounded source references; deterministic code supplies exact quotations. Interpretation remains unverified. Plans resolve literal aliases against one signed request, and holder EIP-712 approvals gate deterministic grant execution.

Imports retain only result/hash/confirmed fields by default. XML trust requires an external certificate and issuer/type scope for an explicitly supported profile. No real provider credentials or authentic samples were available. Public exposure is disabled; only explicit operator opt-in can run the tunnel manager. NFC is clonable discovery transport. No remote deployment or image publisher was run.

## Tests and environment

```powershell
./spring-boot-service/mvnw.cmd -f spring-boot-service/pom.xml package
./.venv/Scripts/python.exe django-service/manage.py test dashboard
node --test spring-boot-service/scripts/test-proof-security.cjs spring-boot-service/scripts/test-verifier-ui.cjs spring-boot-service/scripts/test-bridge-contracts.cjs
node spring-boot-service/scripts/test-contracts.cjs
./tools/rehearse-bridge.ps1 -ProveOffline
./.venv/Scripts/python.exe tools/test-issuance-recovery.py --simulate-persistence-gap
node tools/test-demo-ui.cjs
./.venv/Scripts/python.exe tools/test-local-assistant.py
./.venv/Scripts/python.exe tools/scan-source-secrets.py
./.venv/Scripts/python.exe tools/summarize-verification.py
```

UI test requires Playwright/Chrome; set PLAYWRIGHT_MODULE to the installed module location outside the provided bundled runtime. Logs/artifacts remain ignored under .bridge-data. Test source documents and accounts are intentionally fake. Final counts are derived from Surefire XML, Node/Django logs and integration JSON.

Environment reference: .env.example defines POSTGRES_PASSWORD, LOCAL_AI_ENABLED, OLLAMA_BASE_URL, OLLAMA_TEXT_MODEL, PUBLIC_BASE_URL, PUBLIC_EXPOSURE_OPT_IN, PUBLIC_ALLOWED_HOSTS, SETU_CLIENT_ID/SECRET/PRODUCT_INSTANCE_ID/DOCUMENT_TYPE/ORG_ID/DOWNLOAD_HOSTS and IMPORT_TRUSTED_CERTIFICATE/ISSUER/TYPE. Seed generates test-only registry/governance/signer settings in ignored demo.env. Never commit this generated file or real keys. Native launcher uses its separate isolated DB and YAML config; it does not load retained legacy application.properties.

## Gotchas and open items

Windows PowerShell, Java 17, Python 3.12, Node 25 tested; Node 22 configured for CI. Do not use Bash brace expansion in PowerShell. Managed timestamps can deserialize as DateTime in PowerShell 7; stop handles both typed dates and strings. Chain/code/governance pins must match retained seed state; seed fails closed on mismatch. Cold GPU kernel/model startup exceeded the interactive timeout; warm models or use manual fallback.

Docker engine failure is an inaccessible stale socket. Automatic approval review rejected removal by policy. No cleanup bypass was attempted. Compose and remote CI remain unverified. Ganache is archived with known audit findings; loopback public fixtures only. Native launcher assumes an occupied matching loopback port belongs to the intended service, so use an isolated operator environment. Production authority/custody, crash reconciliation, provider cancellation, authentic schemas, tunnel and hardware NFC remain open; no routine design question or approval is pending.
