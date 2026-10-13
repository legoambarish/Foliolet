# Codebase baseline, 13 October 2026

Inspected all substantive Java controllers/services/entities/repositories/tests, Solidity contracts and compilation scripts, Node proof implementation/tests, Django settings/views/security/cache/tests/templates/static UI, local startup/watcher/live test tooling, tracked documentation and package configurations before product edits. Third-party vendored fonts/ethers/QR, lockfiles, Maven wrapper and generated ABI/bin are dependency or generated artifacts. Existing untracked evolution notes and output artifacts are user property and are preserved.

Initial branch codex/ps32-proof-wallet at 435f5e6466468fac40304c8081b358a83b727450, tracking origin/main. Main c04741ee68563566dc82ab4e71b97c3898714f72. Created testbuilds from current HEAD; no remote writes. Initial dirty state: docs/EVOLUTION_FROM_EVIDENTIA.md and output/ only.

Current stack: Spring Boot 4.1.1/Java 17, Django 6.1, PostgreSQL, Web3j 4.10.3, Solidity 0.8.19, ethers 6.15.0, Ganache 7.9.2. Existing selective registry has one custodial operator, permits self-enrollment and holder-controlled first-seen observations, and rejects unsupported issuer assurance. Grants carry an EIP-191 platform signature. The holder does not yet independently authorize a bundle. Reader already requires external contract/operator/chain pins. AES-GCM vault and per-leaf salts work. Legacy OpenRouter AI must be disabled for the new run.

Migration: new bridge tables, governed contract and protocol coexist with retained legacy data. No old facts become issuer evidence. New demo chain and database state are isolated from .local-data. Reuse canonicalizer, Merkle engine, vault, Basic/BCrypt account isolation and local typography; add explicit governance/issuer/verifier roles and browser holder keys. Existing test context mocks the old chain, so new chain initialization is feature-gated in those tests.

Baseline reruns: Maven 14/14, Django 19/19, Node verifier 22/22, and real in-memory EVM legacy contract suite passed. These are local baseline results, not production certification. Docker engine and Ollama were initially unavailable.
