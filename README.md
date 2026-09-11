# Evidentia: Secure Digital Document Management System (26190)

(Prototype)


<img src="/images/adminlandingpage.png" alt="Image of the admin page">

The image displays the initial login view of Evidentia's dashboard, as simple as it may look, there's a lot to it, read through this README to know more




Two services, run independently:

See each service's own README for setup and details. This file covers the problem being solved, how the two services fit together, and how to build and run the whole thing.

## Problem Statement

**PS ID:** SIH26190
**Title:** Secure Digital Document Management System for Legal and Investigation Documents
**Organization:** Ministry of Home Affairs
**Department:** National Crime Records Bureau (NCRB), Women Safety Division
**Category:** Software
**Theme:** Blockchain & Cybersecurity

Law enforcement agencies, courts, legal departments, and investigative organizations handle large volumes of sensitive documents across a case lifecycle, including FIRs, investigation records, witness statements, charge sheets, court filings, evidence records, and forensic reports. Many organizations still rely on paper based or fragmented digital storage, which causes slow document retrieval, unauthorized access risk, tampering risk, no version control, poor inter department collaboration, and weak auditability.

## Proposed Solution

We are building a Secure Digital Document Management System (DMS) that lets authorized personnel securely store, organize, retrieve, and share legal and investigation documents tied to a case.

Core capabilities for the prototype:

- Role based access control, so only authorized roles can view or act on a given document
- Centralized document upload and storage with case level metadata
- A full audit trail that records who viewed, uploaded, or modified a document, and when
- Search and filter of documents by case ID, document type, and date

How it addresses the problem:

- Replaces fragmented, paper based storage with a single system of record per case
- Enforces access control at the API layer instead of relying on manual, physical restriction
- Makes every document interaction traceable, which directly targets the auditability gap named in the problem statement
- Lays the groundwork for tamper evidence and version history as the system matures beyond the prototype

Innovation and uniqueness:

- The audit log is a first class part of the data model, not an afterthought bolted on later
- The architecture separates the system of record from the reporting and oversight layer, so investigative staff and oversight/admin staff interact with purpose built interfaces instead of one generic dashboard
- Tamper detection covers two separate time windows rather than one: a local file watcher independently fingerprints a document the moment it exists on the officer's machine, before upload, while the on-chain hash covers everything from upload onward. Between them, the system can distinguish "altered before it ever reached us" from "altered after we stored it", most chain-of-custody implementations only cover the second case

## Tamper detection using local Ethereum

The prototype now includes a tamper-evidence layer using **Ganache**, a local Ethereum virtual network, and a small **Solidity** smart contract. The blockchain stores a trusted hash of each uploaded document so the system can later detect whether the stored file has been altered.

How it works:

- When a document is uploaded, Spring Boot reads the file bytes and computes a **SHA-3 hash**
- The document ID, hash, case ID, uploader address, and timestamp are stored by the `DocumentRegistry` smart contract on Ganache
- The document itself remains in the local document store and is not placed on the blockchain
- `GET /api/documents/{id}/verify` reads the current file, recomputes its SHA-3 hash, retrieves the original hash from the smart contract, and compares the two
- If the hashes match, the document is reported as intact; if they differ, the document is reported as potentially altered since upload

The Solidity contract exposes `storeDocumentHash` for anchoring a document hash and `getDocumentRecord` for retrieving the stored record. Spring Boot interacts with the contract through **Web3j**.

Ganache is used as a local single-node Ethereum environment for the prototype. It provides a controlled blockchain environment for development and demonstration without requiring a public Ethereum network. This is intentionally a tamper-evidence mechanism rather than a claim that the overall system is tamper-proof.

This implementation is a deliberate simplification of a distributed blockchain deployment. A single local Ethereum node is sufficient for demonstrating hash anchoring and verification within the scope and timeline of the prototype.

**Important scope note:** the on-chain hash is computed from whatever bytes exist in the file at the moment of upload. `verify()` only detects changes made to the stored file *after* that point, it cannot detect a document that was already altered before it was uploaded. That earlier window is what the local watcher below is for.

### Post-tamper recovery

Detecting tampering on its own still leaves a corrupted or altered file sitting in storage until someone manually intervenes. The prototype now closes that gap for the one case it can act on with confidence: a mismatch caught by `verify()` against the on-chain hash.

How it works:

- At upload time, alongside writing the file to normal storage, Spring Boot also writes an identical copy to a separate backup location, this copy is made in the same request that anchors the file's hash on-chain, so it is guaranteed to correspond to that trusted hash
- When `GET /api/documents/{id}/verify` finds a mismatch between the current file and the on-chain record, it no longer just reports the tamper, it immediately overwrites the live file with the backup copy, restoring it to the exact bytes that were anchored on-chain at upload
- The restore is logged as its own `AUTO_RESTORED` audit entry, separate from the `VERIFY` entry that is always logged regardless of outcome, so the audit trail shows both that tampering was detected and that a restore followed it
- The verify response now also carries a `restored` flag, the Django dashboard uses this to show a distinct amber warning notice ("...has been restored to its last known-good version") rather than lumping a recovered document in with a plain success or plain error message

**Important scope note:** this is a single known-good backup taken once at upload time, not real version history. There is exactly one prior version to fall back to, so "most recent known-good version" and "the original upload" are currently the same thing. If the backup copy itself is missing or unreadable, `verify()` reports the tamper as usual with `restored: false` and an explicit "no backup was available" message, it does not fail silently. A real multi-version rollback system, and protecting the backup from someone with the same database/filesystem-level access that could tamper with the live file in the first place, remain future work rather than something this prototype claims to solve.

## Pre-upload tamper detection (local file watcher)

The on-chain layer above only protects a document from the moment it is uploaded onward. It has no way to know whether the file was already altered before the officer clicked upload, since the hash it anchors is computed at upload time, whatever content exists then is treated as the trusted original. A prototype standalone watcher script closes that earlier gap.

How it works:

- A small script (`tools/local-watcher/watch.py`) watches a designated local intake folder using OS-level filesystem notifications, not polling
- The instant a file appears or changes in that folder, the watcher computes its SHA-256 hash and immediately reports `{filename, hash, timestamp}` to Spring Boot via `POST /api/documents/candidate-hash`, before any upload has happened
- This report leaves the officer's machine immediately: once sent, killing the watcher or editing the file afterward cannot retroactively change what was already recorded server-side
- When that same file is later uploaded, `DocumentService.upload()` looks up the **earliest** reported hash for a file with that name and compares it against the uploaded bytes
- A mismatch means the file was altered locally between first being observed and being uploaded. This is recorded as a `PRE_UPLOAD_TAMPER_DETECTED` audit log entry, and the upload response includes a `preUploadWarning` message, surfaced immediately as a warning banner in the dashboard rather than a generic success message

This is a genuinely separate mechanism from the blockchain layer, no Ethereum, no smart contract, purely Spring Boot and Postgres. The two together cover a document's full lifecycle: creation, upload, and everything afterward, rather than leaving a gap between creation and upload uncovered.

**Honest limitations:**
- Only files that pass through the watched folder get a candidate record. A file uploaded from anywhere else has no earlier fingerprint to compare against, `preUploadWarning` stays `null` in that case, meaning "no claim either way," not "verified clean"
- `POST /api/documents/candidate-hash` is currently open with no authentication, acceptable for a local single-machine demo, not something to expose as-is beyond the prototype

## AI-powered single-document analysis

The prototype now includes an AI analysis layer. This is separate from the tamper-evidence and recovery mechanisms above, it reads and summarizes a single document rather than checking its integrity.

How it works:

- `POST /api/documents/{id}/analyze` loads the document's stored file, extracts its text (PDFBox for PDFs, a plain text read for anything else), and sends that text to an LLM via OpenRouter
- The model is asked to return a summary, a list of key dates, a list of key parties, and a list of flagged clauses worth a reviewer's attention, all as structured JSON
- Every date, party, and clause the model returns is checked against the actual extracted text before being trusted, anything the model claims that is not a genuine verbatim match is silently dropped, this is the main guard against the model inventing details
- Results are stored in a new `ai_insights` table and logged as an `AI_ANALYSIS_RUN` audit entry, `GET /api/documents/{id}/analysis` returns the most recent stored result without calling the LLM again
- The Django dashboard has an "AI Analysis" button next to each document, showing the summary and tables of dates, parties, and flagged clauses, with a "Run Analysis" or "Re-run Analysis" button

**Honest limitations:**
- This only analyzes one document at a time, there is no cross-document search or comparison, that is future work
- Analysis quality depends entirely on how cleanly text extracts from the source file, scanned or image-only PDFs will not extract usefully without OCR, which is not implemented
- Free-tier OpenRouter models are shared and can return `429 Too Many Requests` under load, this is not a bug in the app, retrying shortly or switching `openrouter.model` to a different free model resolves it

**Known bugs and fixes, if setting this up fresh:**
- `LocalDateTime` failing to serialize with a "Java 8 date/time type not supported" error: add the `jackson-datatype-jsr310` dependency to `pom.xml`, and register `new JavaTimeModule()` on the `ObjectMapper` used in `AiAnalysisService`
- `Cannot resolve symbol 'datatype'` shown in the IDE after adding the import: the dependency is missing from `pom.xml`, add it explicitly rather than relying on a transitive include, then reload the Maven project

## How the two services talk to each other

Communication is one directional. The Django dashboard calls the Spring Boot REST API over HTTP. Django has no direct database access to Spring Boot's data, and Spring Boot has no dependency on Django at all, it can run and be fully tested on its own.


## Contract between the two services

Django's `api_client.py` was originally built against a stubbed version of this contract before the real Spring Boot endpoints existed, so it could be developed in parallel. The two are now aligned on:

| Endpoint | Purpose | Access |
|---|---|---|
| `POST /api/auth/register` | Create a user | Open |
| `POST /api/auth/login` | Verify credentials, return a token | Open |
| `GET /api/documents` | List documents (role filtered) | Authenticated |
| `POST /api/documents` | Upload a document | Authenticated |
| `GET /api/documents/{id}` | View one document | Authenticated, owner or ADMIN |
| `PUT /api/documents/{id}` | Update a document's metadata (case ID, document type) | Authenticated, owner or ADMIN |
| `DELETE /api/documents/{id}` | Delete a document and its file | Authenticated, owner or ADMIN |
| `GET /api/cases` | List case summaries (derived, not a real entity) | ADMIN |
| `GET /api/cases/{caseId}` | Single case detail | ADMIN |
| `GET /api/audit-log` | Full or filtered audit trail | ADMIN |
| `GET /api/documents/{id}/verify` | Verify current file against the on-chain hash | Authenticated, owner or ADMIN |
| `POST /api/documents/{id}/analyze` | Run AI analysis on a document | Authenticated, owner or ADMIN |
| `GET /api/documents/{id}/analysis` | Retrieve the most recent AI analysis result | Authenticated, owner or ADMIN |
| `POST /api/documents/candidate-hash` | Report a pre-upload file hash from the local watcher | Open |

Field names in every response are chosen to match what `dashboard/api_client.py` and the Django templates already expect (`documentId`, `title`, `uploadedBy`, `auditId`, `performedBy`, `performedAt`, etc), not Spring Boot's internal naming, so no translation layer is needed on the Django side.

## How to build

### 1. Spring Boot service (system of record)

**Requirements:** Java 17+, Maven, PostgreSQL running locally, Node.js/npm, and Ganache.

1. Install and start **Ganache**:
   - Install Ganache locally and start a local Ethereum workspace/network
   - Keep the RPC endpoint and funded account details available, as Spring Boot will use them to deploy and call the smart contract

2. Install the Solidity compiler used by the project:
```bash
   npm install solc@0.8.19
```
This creates the local Solidity toolchain used to compile `DocumentRegistry.sol`.

3. Compile the smart contract from the project root:
```bash
   npx solcjs --bin --abi \
     -o src/main/resources/solidity.DocumentRegistry \
     contracts/DocumentRegistry.sol
```
The generated ABI and bytecode files should be available as:
```text
   src/main/resources/solidity.DocumentRegistry/DocumentRegistry.abi
   src/main/resources/solidity.DocumentRegistry/DocumentRegistry.bin
```

4. Configure `application.properties`:
   - Set the PostgreSQL username and password
   - Set the Ganache RPC URL
   - Set the **private key of the funded Ganache account** used by Web3j
   - Leave `blockchain.contract-address` blank for the first run if the application should deploy the contract automatically

5. Start Spring Boot once with the contract address blank. The application deploys `DocumentRegistry` to Ganache and prints the deployed contract address in the console.

6. Copy the deployed contract address into:
```properties
   blockchain.contract-address=0x...
```
Then restart Spring Boot so subsequent uploads and verification calls use the deployed contract.

7. Create the database:
```bash
   createdb dms_db
```
or from inside `psql`:
```sql
   CREATE DATABASE dms_db;
```
8. Copy the properties template and fill in your real local credentials:
```bash
   cd spring-boot-service/src/main/resources
   cp application.properties.example application.properties
```
Then edit `application.properties` and set `spring.datasource.username` / `spring.datasource.password` to your local Postgres user.
9. Build and run:
```bash
   cd spring-boot-service
   mvn clean install
   mvn spring-boot:run
```
Runs on `http://localhost:8080`.

10. Verify the blockchain-backed tamper detection:
- Upload a document through `POST /api/documents`
- Note the returned `documentId`
- Verify it through `GET /api/documents/{id}/verify`
- A matching file should return the successful integrity message
- To demonstrate tampering, modify the stored file after upload and run the same verification endpoint again. The recomputed hash will differ from the on-chain hash and the response will report that the file may have been altered

11. Run the local watcher script for pre-upload tamper detection (optional, but needed to demo that layer):
```bash
   cd tools/local-watcher
   pip install watchdog requests
   mkdir -p ~/dms-intake
   python watch.py ~/dms-intake
```
Drop a file into `~/dms-intake`, then upload that same file through the dashboard or API. If it was edited after being dropped in but before upload, the upload response includes a `preUploadWarning` and a `PRE_UPLOAD_TAMPER_DETECTED` audit log entry is recorded.

12. Set up AI-powered document analysis (optional, but needed to demo that layer):
- Export your OpenRouter API key in the terminal before starting Spring Boot:
```bash
   export OPENROUTER_API_KEY=sk-or-v1-...
```
- In `application.properties`, set the model to use:
```properties
   openrouter.model=meta-llama/llama-3.1-8b-instruct:free
```
Check OpenRouter's current model list if this exact free model is no longer being served, free-tier availability shifts over time
- `openrouter.api-key=${OPENROUTER_API_KEY:}` should already be present in `application.properties.example`, this reads the key from the environment variable rather than storing it in the properties file directly

### 2. Django dashboard (reporting/oversight layer)

**Requirements:** Python 3.11+, pip.

```bash
cd django-service
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
```

Point it at the real Spring Boot API instead of stub data:
```bash
export DJANGO_USE_STUB_API=false
export SPRING_BOOT_API_BASE_URL=http://localhost:8080
```

Run it:
```bash
python manage.py runserver
```
Runs on `http://localhost:8000`.

### 3. Register your first users

The dashboard has no signup page, users are created directly against the Spring Boot API. Register at least one ADMIN, since `/api/cases` and `/api/audit-log` return 403 for an OFFICER, and you'll want both roles to test the dashboard's restricted-view handling:

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin1","password":"adminpass","role":"ADMIN"}'

curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"officer1","password":"officerpass","role":"OFFICER"}'
```

Then log in through the dashboard at `http://localhost:8000` with either account.

## CRUD operations via curl

Reading data (cases, documents, audit log) is easiest through the dashboard once you're logged in, that's what it's for. The commands below cover Create, Read, Update, Delete, and document integrity verification.

### Create

**Register a user** (shown above), and **log in** to verify credentials directly:
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"officer1","password":"officerpass"}'
```

**Upload a document:**
```bash
curl -X POST http://localhost:8080/api/documents \
  -u officer1:officerpass \
  -F "file=@/path/to/some/file.pdf" \
  -F "caseId=CASE-001" \
  -F "documentType=FIR"
```

### Read (also available via curl, if you want to bypass the dashboard)

```bash
# List documents (role filtered)
curl -u officer1:officerpass http://localhost:8080/api/documents

# View one document
curl -u officer1:officerpass http://localhost:8080/api/documents/1

# Cases and audit log require an ADMIN account
curl -u admin1:adminpass http://localhost:8080/api/cases
curl -u admin1:adminpass http://localhost:8080/api/audit-log

# Verify document integrity against the hash stored on Ganache
curl -u officer1:officerpass http://localhost:8080/api/documents/1/verify
```

### Update

**Update a document's metadata** (case ID and/or document type only, not the file itself, owner or ADMIN):
```bash
curl -X PUT http://localhost:8080/api/documents/1 \
  -u officer1:officerpass \
  -H "Content-Type: application/json" \
  -d '{"caseId":"CASE-002","documentType":"CHARGE_SHEET"}'
```

### Delete

**Delete a document and its stored file** (owner or ADMIN, cannot be undone; the audit log entry survives independently, see the AuditLog model for why):
```bash
curl -X DELETE http://localhost:8080/api/documents/1 \
  -u officer1:officerpass
```

### Pre-upload hash reporting

This one isn't meant to be called by hand, it's what `tools/local-watcher/watch.py` calls automatically, shown here for completeness:
```bash
curl -X POST http://localhost:8080/api/documents/candidate-hash \
  -H "Content-Type: application/json" \
  -d '{"filename":"test-report.txt","sha256Hash":"<sha256 hex digest>"}'
```

## Known gaps, honestly listed

- No real `Case` entity, `title` and `status` on case summaries are placeholders
- Blockchain integration currently uses a local Ganache network for the prototype; a distributed multi-validator deployment is not implemented
- The Django session stores the raw password for reuse as Basic Auth on later calls, acceptable for a localhost prototype, not something to carry into a real deployment
- `POST /api/auth/login`'s "token" is a Basic Auth string, not a real bearer token, a deliberate simplification given the timeline
- Pre-upload tamper detection only covers files that pass through the watched intake folder, a document uploaded from anywhere else has no candidate hash to compare against
- `POST /api/documents/candidate-hash` is unauthenticated, acceptable for a local single-machine demo, not something to expose beyond the prototype as-is

## Implementation Tasks

### Spring Boot service
- [x] Core entities, RBAC, document upload/retrieval, audit logging
- [x] `/api/cases`, `/api/audit-log`, `/api/auth/login` to match the Django contract
- [x] Update and Delete endpoints for documents, with matching audit log entries
- [x] On-chain (Ganache/Web3j) tamper-evidence and document hash verification layer
- [x] Pre-upload tamper detection via local file watcher and candidate-hash comparison
- [ ] Real `Case` entity if time allows

### Django service
- [x] Case overview, case detail, document list, audit log pages, built against stub data
- [x] Real login page, session-based auth, logout, per-session credentials used on every API call
- [x] Graceful handling when an OFFICER session hits an ADMIN-only endpoint (restricted notice instead of a crash)
- [x] Switch to live Spring Boot data and verify all four pages render correctly
- [x] Upload form calling `POST /api/documents`
- [x] Edit and delete document UI, matching the Spring Boot PUT/DELETE endpoints
- [x] Pre-upload tamper warning surfaced on the upload page, distinct from the normal success message

### Later, after the presentation round
- [x] LLM-based document analysis (summarization, detail extraction)
- [ ] Document version history