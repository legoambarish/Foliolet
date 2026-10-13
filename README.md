# Foliolet Evidence Bridge

Share the fact, inspect the authority, reproduce the decision.

A simulated university issues enrollment and CGPA-threshold evidence. The holder signs a disclosure of exactly the facts requested by a named verifier. The verifier checks scoped issuer authority, commitment membership, holder authorization, policy and chain lifecycle, then saves a signed decision. Name and exact CGPA can remain absent. PASS describes compatibility with this test policy; factual truth remains UNKNOWN.

This branch implements the supplied Phases 0 through 4 with Spring Boot, Django, PostgreSQL, Solidity/EVM and a custom salted-Merkle/EIP-712 protocol. It intentionally departs from the report's TypeScript/SD-JWT and optional-chain recommendations. There is no ZK, SD-JWT conformance, real institutional certification or DigiLocker partnership claim.

## Run locally

On Windows PowerShell from this directory:

```powershell
./tools/start-bridge-demo.ps1
```

Prerequisites: Java 17, Node 22 or later, Python 3.12, network access for the initial dependency downloads. The script provisions isolated portable PostgreSQL when absent, installs project dependencies when absent, builds Spring, starts the persistent local chain, provisions public test actors/pins, and starts the app and independent reader. It preserves the original wallet data. Services bind to loopback.

| URL | Purpose |
| --- | --- |
| http://127.0.0.1:8000/bridge/ | Issuer, governance, holder and verifier desks |
| http://127.0.0.1:8090/ | Independent package reader |
| http://127.0.0.1:8080/api/public/health | Spring health |
| http://127.0.0.1:8001/discover/ | Optional restricted local public preview |

Demo accounts: `governance`, `university`, `employer`, `rogue`, `holder-a`, `holder-b`, `internship-verifier`, `tenant-verifier`. All passwords are the public test fixture `Foliolet-Demo-2026!`. Generate a holder key in the browser and export an encrypted backup before signing. Never use these identities or the fixed chain mnemonic for real assets.

```powershell
./tools/start-bridge-demo.ps1 -SkipBuild -WithAI -WithPublicPreview
./.venv/Scripts/python.exe tools/pull-model.py qwen3:4b
./.venv/Scripts/python.exe tools/warm-models.py
./tools/rehearse-bridge.ps1 -ProveOffline
./tools/reset-bridge-demo.ps1 -Launch
```

AI and public preview are optional. Warm-up attempts gemma3:4b first if downloaded and leaves qwen3:4b loaded last. Exact search, manual approval and all proof verification continue with AI stopped. Reset archives isolated demo state and creates a new chain; saved receipts must be checked against their corresponding archived chain.

Container command:

```sh
docker compose up --build
```

Compose uses dev defaults even without `.env`. Reset its own volumes with `docker compose down -v`. Compose configuration was validated, but Docker image build and stack boot were not executed successfully on this host because the engine is unavailable. Native launch, reset, restart and rehearsal were executed. Do not interpret CI source as an executed CI result.

## Demonstration

Follow the [exact runbook](docs/DEMO_RUNBOOK.md). First show real test-issuer issuance, signed request and two-fact holder approval. Then show the rogue converter refusal and current FAIL after revocation alongside saved historical PASS. Finally stop Spring, Django and AI and verify directly through the independent reader. Stop RPC too and show UNKNOWN.

The assistant can search source passages, highlight quotations, flag clauses for review and propose a bounded disclosure plan. A holder confirmation card and signatures are mandatory. Models cannot issue evidence, widen requests, approve or execute on their own.

Imports support an always-available XML path, explicitly simulated mock, and credential-gated Setu sandbox adapter. Real provider access and authentic issuer schemas were not available. Importing or reviewing fields never promotes their authority. Static NFC/QR is discovery transport, not secure card possession.

## Evidence and limitations

[Actual verification](docs/FINAL_VERIFICATION.md), [machine-derived results](docs/verification-results.json), [phase ledger](AGENT.md), [architecture decisions](docs/ARCHITECTURE_DECISIONS.md), [codebase baseline](docs/CODEBASE_BASELINE.md), [PS32 sources](docs/PS32_REQUIREMENTS.md), [judge FAQ](docs/JUDGE_FAQ.md), [local model measurements](docs/LOCAL_AI_BENCHMARK.md), [NFC/offline checklist](docs/NFC_AND_OFFLINE.md), and [labeled backup recording script](docs/BACKUP_VIDEO_SCRIPT.md).

Governance and issuer signers are local public test identities; governance is trusted. Browser compromise or lost signing keys remains a custody risk. Commitments and addresses are linkable. Downloaded packages can be copied; server expiry/revocation prevents further release but cannot erase copies. Real issuer/provider onboarding, production custody, container runtime validation, unpatched Ganache development dependencies, physical NFC and external tunnel testing remain gaps. No backup video was recorded and URL-fragment encryption was cut.

The original operator wallet remains visibly labeled legacy and uses a separate contract/assurance model. Its historical documents under `docs/PROTOCOL.md`, `docs/SECURITY.md`, `docs/ARCHITECTURE.md` and `docs/VALIDATION.md` describe that path, not certification of the new bridge. Frozen legacy contracts remain under `spring-boot-service/contracts/legacy/`.
