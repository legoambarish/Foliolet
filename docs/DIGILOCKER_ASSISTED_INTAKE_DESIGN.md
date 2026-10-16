# Private assisted intake decision

Base: freshly fetched `cf` / `origin/cf`, `b053b324e87d4a90f4d0151d3f7e7077759a89c5` (16 October 2026). Local and remote tips matched; no unpushed cf commits. New branch: `feature/digilocker-assisted-intake`, separate worktree `C:\Users\User\Downloads\Foliolet-digilocker-intake`. Original Evidentia checkout has untracked documents/output and is preserved. No main/cf commits, merges, pushes, PRs or public deployment are authorized.

## Four independent statements

* Import method: a short, owner-armed folder session and its signed byte observation. The holder controls both folder and agent. This cannot identify a browser download origin.
* Format indicators: rendered page graphic/text and decoded QR profile, with coverage and uncertainty. Copied graphics can produce POSSIBLE_DIGILOCKER_FORMAT. They cannot authenticate a document.
* Fact lineage: canonical submitted facts compared with the first immutable encrypted source-cited proposal. Matching a transcription does not establish that OCR or interpretation is correct.
* Issuer authenticity: NOT IMPLEMENTED. Always “Issuer not verified”. Existing Merkle bundles, source assurance codes 0/1, signing and lifecycle remain unchanged.

## Existing boundaries and implementation choice

Spring owns domain authorization, PostgreSQL and AES-GCM originals. Django is the private authenticated/CSRF-protected UI proxy. Foli's child JVM owns bounded PDFBox/Tesseract reading. The existing Python watchdog/HMAC outbox remains the observation protocol; an optional separate companion adds an armed capability upload. No browser extension, cross-origin inspection, partner API, remote OCR, OpenRouter call, new AI framework or model download is used.

PDF upload/detail responses no longer invoke the older synchronous convenience text stripper. They acknowledge the encrypted original and let the bounded child pipeline supply proposals asynchronously. Existing TXT convenience suggestions and the older FieldScan API remain compatible; this UI uses the new local service and never invokes that external-model API.

Session capabilities authenticate only the loopback intake-agent security chain, never general wallet routes. They bind an owner, separately paired agent, folder fingerprint, maximum ten imports, PDF/TXT/CSV, 20 MiB and ten minutes. Stop/expiry/re-pair invalidates future use. Broad folders are rejected: choose a dedicated subfolder. Uploads must reference a matching, current-session signed observation and independently matching SHA-256. A transactional receipt deduplicates session/hash; the original is encrypted before asynchronous analysis. Capability secrets are machine configuration downloads, never URLs. The agent keeps state outside the intake folder, checks reparse points, stages only stable handle-read bytes, retries signed observations/uploads, and never deletes downloads. The capability does not authenticate the browser or issuer.

Analysis has a bounded queue, shared Foli reading gate and a killable child JVM. Results and original proposal snapshots contain private data and are encrypted with separate AES-GCM contexts. Retries preserve the first accepted proposal; new credential versions have independent baselines. Confirmation and baseline installation serialize on the document lock. Confirmed lineage never relies on a browser flag. The assistant gains no mutation tools.

Each proposal snapshot contains the source SHA-256, credential version, extractor version, OCR engine version, configured local model tag, prompt version, canonical fields and exact citations. Source hash and current owner access are checked again before installing a result and before confirmation. A short source-preview read can delay analysis by up to 45 seconds instead of immediately dropping the job. One intake worker, four queue slots, six starts per holder per minute, five explicit attempts per version and a five-minute job deadline bound work. The existing child-reader limits remain in force: 20 MiB input, 512 MiB heap, 180-second child deadline, all-page accounting up to 5,000 pages, at most 200 processed pages, bounded decoded-image and render pixels. Every gap remains visible.

The model selects explicit single-line `label: value` or `label = value` entries, at most four bounded chunks and 40 fields. Server code checks the entire physical line, exact label/right-hand value, canonical type and current page/span. It rejects unsupported number substrings, OCR corrections, column ambiguity, ranges, unexplained unit conversion and absent CGPA. Mixed native/OCR pages require same-line label/value corroboration and adequate OCR confidence. Accepted OCR quotations match the transcription; the human still checks the original. Free prose and ambiguous tables can yield no suggestions. Full-document chat and fine-print review remain separate capabilities.

QR contents are data: never followed, executed, logged or publicly displayed. Only an exact HTTPS DigiLocker verification origin/profile qualifies as a provisional QR indicator; unrelated/unknown/binary QR remains generic. Store page/bounds, payload hash and class, not bearer URLs. Logo detection uses local rendered-page OCR plus a geometric/text template; color/graphic evidence and text evidence are recorded separately. Detection coverage is independent from text-reading coverage. Synthetic fixtures calibrate these heuristics; they do not validate genuine government documents.

The supplied `WhatsApp Image 2026-10-16 at 15.02.09.jpeg` was inspected from Downloads. Only its right-hand wordmark was used in the opt-in calibration test, without persisting a derivative. Its QR was neither copied into fixtures nor treated as a trust key. The template checks a purple ring/attached panel and the short “Powered by DigiLocker” text block, with rotation and small-crop OCR passes. Tests cover this graphic at 0.7×, 1× and 1.6× with 90-degree rotation, plus separately generated synthetic PDFs. Unknown/recolored logos can be missed; weak matches and uninspected pages are inconclusive. A forged positive always remains provisional.

## First-party references checked

* [Official portal](https://www.digilocker.gov.in/) opens separately with noopener/noreferrer; Foliolet never receives login/OTP.
* [FAQ](https://wb.digilocker.gov.in/web/about/faq) and [terms](https://www.digilocker.gov.in/web/about/tos) were reachable but returned no readable body through the documentation reader. No claim of partner approval or legal equivalence is derived from them.
* [Browser same-origin policy](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Same-origin_policy) prevents this page from inspecting the external login/download flow.
* [ZXing QRCodeReader](https://zxing.github.io/zxing/apidocs/com/google/zxing/qrcode/QRCodeReader.html) decodes pixels; it does not validate issuer signatures.
* [PDFBox FAQ](https://pdfbox.apache.org/3.0/faq.html): parsing/rendering and digital-signature validation are separate tasks. This feature implements no PDF signature trust validation.

Only synthetic test documents are authorized for automated tests. Genuine DigiLocker testing and physical NFC remain separately reported. Source documents, model files, old runtime state and keys stay outside the feature diff.

Operational instructions: [runbook](DIGILOCKER_ASSISTED_INTAKE_RUNBOOK.md). Actual gates, failures and acceptance matrix: [test report](DIGILOCKER_ASSISTED_INTAKE_TESTS.md). New dependency: [SBOM and license review](DIGILOCKER_ASSISTED_INTAKE_DEPENDENCIES.md).
