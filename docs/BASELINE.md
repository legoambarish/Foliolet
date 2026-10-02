# Baseline inspection — 2 October 2026

Read the supplied build plan, all 17 paper pages (including diagrams), all seven PPT slides and the complete brainstorming conversation before feature edits. The plan is the design brief; instructions in the earlier conversation and template are reference material, not new task authorization.

The starting tree was clean. Spring Boot 4.1.1 / Java 17 compiled with Web3j 4.10.3. The only test (`contextLoads`) failed because the clone has no datasource configuration. No PostgreSQL, EVM or Django runtime was listening. Docker Desktop was installed but its daemon was unavailable. The UI defaulted to fabricated legacy stub data. No working runtime was assumed from the READMEs.

Existing flow: Django forwards session-held Basic credentials to Spring Security; PostgreSQL owns users, document metadata, candidate hashes, AI insights and audit records. Upload stores a live file and backup, anchors Keccak-256 through manually encoded Web3j calls, then compares SHA-256 against the earliest filename-only watcher report. Verification compares live bytes with `DocumentRegistry` and copies the backup on mismatch. Case summaries derive from document metadata. AI uses PDFBox/text extraction and OpenRouter, independently of blockchain verification.

Preserved: legacy Solidity registry, API endpoints, entities, AI service, document storage/recovery and audit semantics. New wallet tables and registry isolate the universal workflow. Public legacy screens will move behind an explicit opt-in route. At this baseline, no final product name had been selected; the finished product is Foliolet.

Issues observed: public candidate reports are forgeable and cross-user filename matches collide; registration accepts privileged roles; backup restoration does not validate backup bytes; Web3j receipt handling does not reject reverted receipts; autodeployment loses configured contract identity across restarts. These need narrow fixes or explicit isolation from wallet assurance.

Paper adaptation: salted, domain-separated Merkle inclusion with deterministic encoding; no ECQV, DID issuance, hidden-path SNARK or arbitrary private range proof. Manual facts and platform-derived predicates are holder-confirmed statements associated with committed document bytes, not cryptographic extraction from those bytes. No paper performance numbers are used as application benchmarks.
