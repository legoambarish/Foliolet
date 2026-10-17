# P0 performance and trust delivery

Date: 17 October 2026. Baseline: remote `main` at `ecc7c9646876e41e7947f4be4148eed2bfb4c3ad`. Implementation HEAD: `6307fd659a57aba892fae67093ff20ade2d8b1ac` (preceded by `8ead65c8c5206beaa215fe7c1d8012c7e1141dbb`). Worktree: `Foliolet-p0-performance-trust`. [Implementation branch](https://github.com/legoambarish/Foliolet/tree/codex/p0-performance-trust). Original branches, application databases, keys, models and chain were preserved. This report distinguishes measured results from limitations; no issuer authenticity or universal accuracy claim is made.

## Root causes and changes

| Problem | Evidence and cause | Implemented behavior |
|---|---|---|
| Slow local answers | Actual Qwen CPU execution: `size_vram=0`; baseline first invocation 8.431 s, later 3.482/3.408 s for a short general question. Inference accounts for almost all of these timings. Smaller context did not improve warm performance. | Preserve the working Qwen configuration; reuse identical completed authorized requests in bounded memory; show a verified-source checklist before semantic review finishes. |
| Extraction perceived as AI latency | `LayoutFacts` already uses deterministic geometry first. Its model is invoked only when no deterministic associations exist. PDF rendering, OCR and inspection dominate representative fixtures. | Retain deterministic extraction and uncertain-field review gates. Do not add a remote model to routine extraction. Reserve a separate portion of the existing reader deadline for indicators. |
| Supplied QR never decoded | ZXing Java did not decode the dense supplied image. Complementary local ZXing-C++ did. In a PDF, PDFBox's 130-DPI interpolation loses this code, while 200 DPI succeeds. | Bounded local complementary decoder, original/inverted Java passes and tiled quiet-zone enlargement; merge distinct results across decoders; independent 200-DPI indicator rendering with the existing 8 MP limit. Preview remains 130 DPI. |
| Structured payload fell through | Exact-origin HTTPS recognition existed, but non-URL JSON arrays were generic. | Recognize one strictly bounded empirical array profile; preserve unknown variants as unknown. No URL is followed or ciphertext interpreted. |
| Branding read as weak resemblance | Thin small wordmark OCR was unreliable even for the supplied complete graphic. | A deterministic normalized pixel template checks silhouette and interior wordmark at multiple quarter-turns; existing bounded OCR remains a fallback. |
| Quiet/combined stamps | Backend legacy indicator combined QR/logo; static template and polling JS made separate interpretations. | Server computes separate check states and rendering descriptors. Both sender paths consume these descriptors, with explicit details and green only for `PASSED`. |
| Recipient lacked lineage | Intake metadata was outside the signed presentation; the recipient had no selected-fact comparison. | Add an explicitly versioned, signed, selected-fact status extension. Optional document checks require the holder's separate checkbox. Strict Java, Django and JS schema gates are synchronized. |

## AI routing inventory and decision

| Subsystem | Current route | Limits and authority |
|---|---|---|
| General and document Ask Foli | Local Ollama by default; optional Gemini Flash Lite | Read-only text output. Same exact-source citation verifier after either provider. No tools or source-file upload. |
| Whole-document review | Immediate local deterministic checklist, then existing bounded local semantic batches | Preview explicitly has incomplete semantic coverage. Completion and citations retain existing checks. |
| Clear labels, values and tables | `LayoutFacts`, deterministic | No model calls on the four benchmark fixtures; geometry, source spans and original literals remain authoritative. |
| Ambiguous layout fallback | Existing local `modelPairs` | Model can choose bounded existing source cell IDs only; geometry rechecks reject cross-source/nonadjacent links; uncertain results require review. |
| PDF/text extraction and OCR | PDFBox, Tesseract and configured local complementary OCR | Killable reader subprocess, bounded heap/time/pixels/pages, private temporary files. Gemini receives none of this pipeline's input automatically. |
| QR, branding, PDF signature mathematics | Deterministic local code | No model, remote verification service or issuer authority. |
| Legacy analysis/field scan | Existing separately gated OpenRouter paths | Not routed into Gemini, disabled in the demo launcher with an empty OpenRouter key; legacy explicit-consent/default-deny controls retained. Not benchmarked because disabled. |

The 10-case fictional provider rubric favored `gemini-3.5-flash-lite`: 8/10 passes and 1.0465 s median, versus Qwen 6/10 and 3.3595 s median. This is a small provider-only benchmark, not a product-wide accuracy score. Flash Lite still failed definition/citation or write-request rubric cases; the application retains independent read-only and citation gates. `gemini-3.8-flash` passed its first six cases, then returned four HTTP 429s. It is not the default. A separate actual Java adapter smoke test passed a fixed fictional general question and a grounded question with a validated citation. No user document or private conversation was used in cloud experiments.

Application streaming of unvalidated tokens was not enabled: source references must pass validation before being shown as supported. Provider streaming was measured only to distinguish first token from a validated answer. The useful responsiveness change is early checked review evidence, plus memory-only reuse. This does not make uncached CPU inference twice as fast.

Completed-response reuse is keyed by owner, source bytes hash, document version, credential status, mode and exact request including history/consent. Every release reopens the authorized source. Source changes, status changes, access loss, expiry, cancellation and forgetting prevent reuse. It shares the existing 32-job/retention bounds. It is not a durable chat store. Restart clears it. Review previews are released only after current source authorization and disappear on cancellation/failure.

## Gemini privacy and availability

The supplied key successfully listed models and generated fictional responses. Neither result establishes the API project's billing tier. Actual account/tier remains **UNVERIFIED**. The application stays disabled by default and the private demo was never enabled for cloud traffic.

Activation requires all of: `FOLI_GEMINI_ENABLED=true`, an independently reviewed active paid-service policy recorded as `FOLI_GEMINI_DATA_POLICY=paid-reviewed`, a server-side `GEMINI_API_KEY`, and per-request user consent. Missing/unknown/unpaid configuration refuses application text before request construction. The checkbox states that the question, conversation context and selected text excerpts leave the device. It resets after submission. An environment value is an operator attestation, not automatic billing verification; do not set it merely because a key works.

Only a fixed Google HTTPS origin is used, with no proxy/redirects, no tools, file APIs or URL fetching, a 16,000-character input bound, 900 output-token bound and 20-second request deadline. Gemini failures/rate limits fall back to local Ollama and report that fallback. Missing local model still leaves manual facts and deterministic review available. Raw provider error bodies/credentials are never logged. Keys are not serialized into reader subprocess configuration or frontend health responses. The response is size-checked after the trusted-provider body arrives; this is not a hard streaming allocation ceiling.

Official references consulted: [Gemini terms](https://ai.google.dev/gemini-api/terms?hl=en), [models](https://ai.google.dev/gemini-api/docs/models), [GenerateContent API](https://ai.google.dev/api/generate-content), [pricing](https://ai.google.dev/gemini-api/docs/pricing?frmapp=yes). Unpaid terms are unsuitable for confidential/private application inputs. Published Flash Lite text pricing was $0.30 input/$2.50 output per million tokens at research time; estimates in `METRICS.json` use observed usage, not an invoice or proof of billing tier. Model availability, prices and quotas may change.

## Observed QR format and authenticity boundary

The supplied reference decodes locally to a four-string array. The supported empirical profile has the observed headers `5005`, `1`, `Y` followed by canonical Base64 representing 64–2048 bytes. Parser input is bounded to 4096 characters; extra/trailing JSON, wrong types, unknown headers and malformed Base64 are not a positive structured match. This is deliberately a narrow profile, not a universal DigiLocker format specification.

The [official DigiLocker circular](https://cdn.digilocker.gov.in/assets/img/circulars/Letter-to-All-State-Governments-UTs.pdf) describes encrypted QR/app verification. No authoritative public specification mapping these three headers, an applicable issuer public-key set, or an independent verification procedure for this particular envelope was established. The encoded bytes' compression, cipher, signature and authority semantics remain unknown. Base64 is not cryptographic verification. No decryption, remote lookups or invented issuer authentication were implemented.

The stages remain separate: the decoder locates/decodes pixels; `qrKind` classifies supported content; status reports a format match; cryptographic QR authenticity remains unverified; issuer authorization remains unverified. The UI does not claim a separately persisted located-but-undecoded state: an unreadable candidate remains inconclusive. Raw payloads/actual supplied QR image are not in Git, public metadata or application logs. Private decoder IPC is deleted after use. The only supplied asset retained is the non-personal branding crop, solely as a detector reference; it is not a claim of affiliation or an independently licensed brand grant.

Fabricated/copy-pasted data that exactly fits this public profile can pass **format detection**. Copied logos can pass **branding presence**. Tests explicitly retain this distinction. Only `https://verify.digilocker.gov.in` with the existing strict URL conditions qualifies for the URL profile; arbitrary URLs are never opened.

## Exact status specification

| Stamp | Positive backend condition | Other states and meaning |
|---|---|---|
| DigiLocker-associated QR | At least one actually decoded supported URL or empirical structured profile in the source-bound report | No report: not checked; attempted without supported decode: inconclusive; text/CSV: not applicable. Never issuer authentication. |
| DigiLocker branding | Qualified local graphic/OCR recognition in the report | No report: not checked; attempted without sufficient evidence: inconclusive; text/CSV: not applicable. Copied branding has no authority. |
| Imported with Foliolet | Recorded watcher-assisted method with session and observation identifiers | Manual upload is not applicable; a failed import that never enrolled a document cannot receive a positive stamp. Origin website is not authenticated. |
| PDF signature integrity | Supported detached PKCS#7/CAdES signature mathematics with valid byte-range/current-file coverage | Unsigned: not applicable; invalid signature: failed; unsupported/incomplete inspection: inconclusive/not checked. Embedded self-signed certificates can pass mathematics, never issuer trust. |
| Facts modified after extraction | Server canonical comparison finds edited, added or removed fields | Changed is caution; unchanged stays quiet. Missing baseline is not assessed; mismatched source/version is stale. Neither is unchanged. |
| Issuer authority | No positive issuer condition implemented | Always unverified. No QR/logo/import/PDF-mathematics shortcut changes it. |

Green `pass` + check icon means the stated positive check only. `fail` is red, `MODIFIED` caution, and unverified/inconclusive/not-checked/not-applicable/unchanged are quiet with explicit wording. Sender stamps include explanatory details; recipient wording describes recorded states associated with the signed version. Reinspection may update inspection evidence, but never rewrites a confirmed historical extraction baseline.

## Fact lineage and signed protocol

`IntakeMetadata` compares canonical path, label, type and value against the encrypted preserved baseline, with matching source hash and version. Ordering and legitimate canonical equivalents do not count as changes. A changed path appears as removal/addition, which is accurate relative to the saved fields. A missing or stale baseline is never interpreted as unchanged. Existing confirmation and source-integrity locks remain in place.

The extension schema is `intake-status-v1`. It contains only selected leaf indexes, each with `UNCHANGED`, `EDITED`, `ADDED`, `NOT_ASSESSED`, `STALE_SOURCE` or `DERIVED`, plus support quality of the **original suggestion**. This does not assert that a holder's edited value is supported. Removed or undisclosed fields, old values, history counts and raw source hashes are not added to the extension. Derived facts do not expose their hidden source through this metadata.

Document checks are `NOT_DISCLOSED` unless the holder selects the separate checkbox. Issuer remains `UNVERIFIED`. The platform signature binds all extension values, selected leaf order/indexes and the pre-existing credential/version/anchor/presentation context. Envelope domain byte **4** identifies extended presentations; old envelopes retain domain **3** and the existing Merkle format `salted-merkle-keccak-v1`. The optional field is absent for legacy proofs. Strict JSON migration fills only that absent extension internally; it does not loosen required fields, duplicate keys, scalars or unknown fields. Explicit `null` extensions are rejected. Adding/removing/changing status invalidates the signature. Historical signed proofs remain verifiable, but correctly show no extraction-lineage evidence.

Java and independent JS tests cover tampering and legacy signatures; fresh Django private/restricted profiles and real HTTP/browser runs verify propagation. Cryptographic/platform checking is distinct from on-chain latest status and release policy. Revoked/superseded/expired grants do not become valid because their status metadata is signed.

## Readiness verdict

**Ready for a bounded local PS32 demonstration**, with working detection, actual green state-driven checks, modified/unchanged lineage, signed selected metadata, local fallback and measured repeat-request responsiveness. The supplied dense QR works as an image and as an embedded PDF with the final inspection render. The strongest safe claim is selective disclosure with platform/commitment verification and honest evidence descriptions.

Do not claim independently authenticated DigiLocker issuers, universal QR formats, arbitrary damaged/cropped/skewed logo recognition, general OCR correctness, legal interpretation accuracy, or a universal 2× speedup. Complete branding at tested scales/quarter-turns/monochrome is covered; substantial cropping, severe compression/skew and unknown graphic versions can remain inconclusive. Signature trust-chain validation, PDF transforms/DocMDP semantics and revocation of embedded signer certificates are not implemented by this integrity-only stamp.

The final extraction comparison shows an inspection cost, because the baseline already extracted structured facts without an LLM. Performance details and sample-size caveats are in `PERFORMANCE.md`. Live public Cloudflare transport and Docker daemon execution were not performed; restricted receiver behavior was exercised through the actual local Waitress profile, exact-host/HTTPS middleware, real backend and browser with locally routed HTTPS. Docker configuration and runtime unit checks passed. No real issuer documents, issuer keys or NFC hardware were authenticated.
