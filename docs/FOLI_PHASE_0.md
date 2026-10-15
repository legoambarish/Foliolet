# Foli phase 0 — verified baseline (15 October 2026)

Implementation runs exclusively in the existing `cf` worktree at
`C:\Users\User\Downloads\Foliolet-testcloudflare`. Starting commit:
`504a1872cb921c40e9420df4ab1718aa43a52069`; starting tracked/untracked status is clean.
The Evidentia worktree remains on its original branch and is not an implementation
target. Local main is `c04741ee68563566dc82ab4e71b97c3898714f72`; all starting refs
are recorded in ignored `.local-data/foli/starting-refs.txt`. No remote operations.
Both supplied Markdown documents were read completely. The current implementation
request overrides their historical planning-only/branch-creation instructions.

## Actual architecture and read contract

* Spring Boot 4.1.1 / Java 17, PDFBox 3.0.8, JPA/PostgreSQL and HTTP Basic
  authenticate against the existing users table. Roles: HOLDER, OFFICER, ADMIN.
* Wallet rows hold metadata. Original bytes are AES-256-GCM files with document ID
  as AAD, read through PrivateVault after owner verification. ADMIN does not gain
  access to another holder's wallet. Revocation concerns proof use; an owner can
  still read their retained original under the existing policy.
* Legacy records refer to a separate file store; uploader or ADMIN may read them.
  Foli uses an explicit adapter and never calls the legacy verify/restore method.
* Existing TextExtractionService cuts at 15,000 characters. Foli will use a new
  extractor. FieldScanService and AiAnalysisService call OpenRouter; Foli will
  depend on neither and will have no external fallback or write tools.
* Django uses DB sessions containing the user's Spring credentials server-side.
  Foli proxies will require that session and CSRF for job mutations. Basic auth,
  credentials and internal file paths never enter model messages/browser data.
* Public Cloudflare receiver has a separate URLconf, session key/database/cookies
  and explicit static allowlist. Those files remain unchanged. Foli routes and
  assets are private-only, with negative route/asset tests.

All source opens and returned job/source results reauthorize, reread the current
original and check its hash/version. Typed IDs distinguish `wallet:` and `legacy:`.
Derived text/jobs are bounded, ephemeral memory with TTL and explicit forgetting;
no durable chat history or embeddings. No authoritative rows, originals, facts,
approvals, grants, shares or chain data are modified by Foli.

## Baseline executed before feature edits

| Command | Actual result |
| --- | --- |
| `spring-boot-service/mvnw.cmd -B -f spring-boot-service/pom.xml test` | 25 tests, 0 failures/errors/skips |
| `.venv/Scripts/python.exe django-service/manage.py test dashboard` | 50 tests passed; system check clean |
| `node --test spring-boot-service/scripts/test-proof-security.cjs spring-boot-service/scripts/test-verifier-ui.cjs` | 22 passed |
| `node spring-boot-service/scripts/test-contracts.cjs` | PASS, real in-process Ganache/EVM; optional native module falls back to JS |

Original output is under `.local-data/foli/baseline-*.log`. Live services were
stopped at inspection; retained runtime data will not be reset or replaced.

## Hardware and design choices

Windows 11 Home 10.0.26200; Ryzen 7 7435HS (8 cores/16 threads); 24,842,968 KiB
visible RAM (~23.69 GiB), ~9.62 GiB free at inspection. RTX 4060 Laptop GPU,
8188 MiB VRAM, driver 591.66, 869 MiB used at inspection. Java 17.0.19,
Python 3.12, Node 25.9.0, Django 6.1. Only Docker Desktop WSL distribution is
installed/stopped. About 62.6 GiB disk free. Native runtime is preferred.

Ollama 0.40.3 and qwen3:4b/gemma3:4b weights exist in another worktree's ignored
demo directory; no Ollama listener and no Tesseract on PATH. Reuse/copy only
immutable runtime/weights into cf state; never write the other worktree's state.
Candidate selection remains subject to measured benchmarks.

Use Spring AI 2.0.1 BOM + explicit Ollama module, compatible with Boot 4.1 per
[official compatibility documentation](https://docs.spring.io/spring-ai/reference/getting-started.html).
No auto-configured model pulls, cloud models, advisors, tools or vector store.
Use bounded lexical retrieval and exact server-generated evidence spans. Tesseract
is a separate local OCR engine; PDFBox extracts/renders only. TXT/CSV preserve
lines, PDF preserves pages. Other formats are explicitly unsupported initially.

Default ceilings: 20 MiB original, 200 processed PDF pages, 1.5 million extracted
characters, 100k characters/page, 8 million rendered pixels, 25s OCR/page,
180s extraction, one extraction/inference worker and a queue of four. Unprocessed
pages receive explicit statuses. Model context is 8192 tokens, package <6 GB.

## Threat model and fixtures

Protect against IDOR (including jobs/source pages), stale hashes/access changes,
source path traversal/symlinks, oversized/decompression-heavy inputs, hung OCR,
prompt injection, model quote fabrication, public receiver route/static leakage,
browser XSS, CSRF, context mixing and unbounded memory/jobs. Host-admin compromise
is outside the existing local development threat model. Matching OCR text is
not a guarantee of visual transcription accuracy or legal correctness.

Fixture matrix: digital and >100-page legal PDFs with a late exception, scans,
mixed/rotated/tiny-footnote/two-column pages, contradictory clauses, PDF passwords,
corrupt/missing/unsupported inputs, TXT/CSV, two holders plus officer/admin,
replacement/deletion, model/OCR outages, concurrency/cancellation, injection and
unanswerable questions. Gold cases and measured results are added in later phases.

Phase 0 gate: baseline passed; authorization, storage and receiver boundaries
traced. Proceed to phase 1 without inter-phase approval.
