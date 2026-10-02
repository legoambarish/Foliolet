# Foliolet backend

Java 17 / Maven wrapper / PostgreSQL / Web3j. The backend owns users, encrypted wallet records, sharing policy, provenance and audit. See [root guide](../docs/RUN_GUIDE.md), [architecture](../docs/ARCHITECTURE.md) and [security boundaries](../docs/SECURITY.md).

From repository root use `tools/start-backend.ps1` after PostgreSQL and EVM are ready. The script reads the ignored local development EVM key only when no key was configured. `application.yaml` supplies loopback demo defaults; environment variables override them. Existing ignored `application.properties` overrides YAML defaults and must be reviewed before pointing at an existing installation. Never overwrite an existing datasource, registry identity or private key merely to run the demo.

`mvnw.cmd -B package` builds the executable jar and runs fourteen tests with isolated H2 and mocked EVM gateway only in test scope. Actual PostgreSQL/Web3j/EVM checks run through `tools/test-live-workflow.py` and `tools/test-live-security.py`. `npm ci` installs the pinned Solidity/local-EVM/independent-verifier tooling; compiled new registry ABI/bytecode are also committed.

New owner routes: `/api/wallet/documents`, document `/claims`, `/anchor`, `/integrity`, `/file`, `/revoke`, `/versions`; `/api/wallet/disclosures`; `/api/wallet/integrity/agents` and `/observations`; `/api/wallet/activity`. Public routes: POST `/api/public/disclosures/{token}/open`, POST `/api/public/verify-bundle`, GET `/api/public/grants/{id}/status`, GET `/api/public/network`. The observation ingress `/api/integrity/observations` validates paired-agent HMAC rather than Basic credentials.

Legacy document/case/audit/analysis endpoints and original DocumentRegistry remain supported. Legacy candidate hashes now require owner authentication. ADMIN cannot be self-registered; existing controlled admin provisioning is separate. Basic authentication is retained and needs HTTPS and a proper token/session redesign before production.
