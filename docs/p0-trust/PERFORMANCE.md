# Measured performance and limits

Raw measurements were taken on this Windows host using the retained baseline production classes and the final branch's classes, local PostgreSQL/EVM/application, Tesseract, and the existing Qwen Ollama instance. The model was CPU-resident (`size_vram=0`). No user model/state was deleted or reconfigured to manufacture a cold start. `METRICS.json` contains the sanitized trial values, usage and costs.

## Direct image and application responsiveness

| Path | Before | After | Interpretation |
|---|---|---|---|
| Supplied image inspection, 3 trials | p50 1194 ms; nearest-rank p95 1404 ms; 0/3 QR, 0/3 qualified branding | p50 218 ms; p95 422 ms; 3/3 QR, 3/3 branding | About 5.5× median improvement while fixing the false negative. Direct image benchmark, not full upload latency. |
| Original application short local chat | First 8431 ms; later 3482/3408 ms | Fresh HTTP question 4431 ms; identical repeats 65/60 ms | CPU inference itself did not improve. Reuse avoids repeated inference under the same authorization/source/status/request. Different history or input is a cache miss. |
| Source-grounded local HTTP chat | Baseline service lacks completed-response reuse | First 8843 ms; identical repeats 78/68 ms, one validated citation | Measured final application; no claim of a matched historical first-request speedup. |
| Whole-document local HTTP review | No result released before semantic completion | First useful checklist 304 ms; completed 8647 ms; repeats 74/73 ms | Early deterministic evidence is useful while full semantic review is pending. The preview is not a completed semantic review. |
| Supplied image embedded in fictional PDF | 130-DPI PDFBox render: QR could not decode | 200-DPI render: QR + branding pass; actual intake completed in 5520 ms | End-to-end single sample, not a p95. Source, anchor, disclosure and recipient checks also passed. |

The first general HTTP job reported 4169 ms of model work out of 4431 ms end-to-end. Document chat reported 7271/8843 ms; review 8354/8647 ms. The balance includes retrieval/indexing, source reauthorization, HTTP and polling, not a separately measured pure queue duration. Polling was 150 ms for these measurements. Cached results retain their original model performance fields; those fields do not mean the model reran. `reused=true` and measured HTTP latency identify reuse explicitly.

The smaller-local-context experiment returned 7993/3521/3554 ms versus baseline 8431/3482/3408 ms. It did not improve warm latency and was reverted. Qwen still uses the existing bounded context/output policy and ten-minute keep-alive. First invocation and warm repeats are reported, but a fully unloaded cold model was not forced because the model instance was shared with existing applications.

## Final sequential extraction comparison

Three cold JVM trials per version/fixture, 24 trials total. The disposable test API was stopped during the final comparison; both versions used the same local OCR configuration and fixture bytes. OS caches and the shared model were not reset. `totalMs` is measured inside the actual intake harness and includes its bounded reader, inspection and field association; `wallMs` also includes outer JVM launch. Three-point nearest-rank p95 is simply the largest observed value, not a stable population-tail estimate.

| Fixture | Baseline p50 / p95 (ms) | Final p50 / p95 (ms) | Fields per run |
|---|---:|---:|---:|
| Native label/value PDF | 1694 / 1719 | 2788 / 2820 | 5 |
| Native table PDF | 1689 / 1694 | 2804 / 2814 | 3 |
| Scanned PDF | 6901 / 6944 | 7574 / 7731 | 3 |
| Synthetic logo + URL QR PDF | 7170 / 7192 | 10444 / 10910 | 5 |

**These first-time PDF paths became slower.** Higher-resolution inspection, another local decoder and graphic/signature checks add work. This is a correctness tradeoff, not an extraction speedup. The copied synthetic graphic uses OCR fallback and is slower than the complete supplied graphic's template match. Do not use the direct-image speedup to describe full document processing.

All 24 runs completed without parser/model failure, retained the expected Math 90 field, and produced **96/96 exact source-aligned citations**. Table headers legitimately produced labels such as “Math marks”; scoring uses the canonical `education.math` path. All 24 had **zero LLM calls** because deterministic association already handled these fixtures. Uncertain scanned associations stayed review-required. The four fixtures are too narrow to infer general document accuracy or an OCR false-positive rate.

Reading/rendering/OCR/indicator time and total time are captured per trial, but this benchmark does not separately attribute each Tesseract/layout engine call. Process-tree RSS was sampled every 200 ms and peaked at **632.3 MiB** across final trials. This includes concurrent reader processes, not the shared Ollama server or total host memory. The pixel matcher/complementary reader increases native-page RSS relative to baseline; no lower-memory claim is made. Historical preliminary 130-DPI/contended measurements were retained privately; final headline extraction numbers use only the final sequential comparison.

## Provider-only fictional rubric

The same ten fixed fictional cases cover fees, negation, exceptions, missing answers, conflicts, prompt injection, definitions, deadlines, write requests and unusual terms. Provider cold state cannot be controlled. The script checks required facts, evidence IDs and injection/read-only behavior, not just JSON syntax. Raw model output has no signing or issuer authority.

| Provider | Rubric passes | Successful response p50 / p95 | Median first token | Failures |
|---|---:|---:|---:|---|
| Local Qwen 3 4B instruct | 6/10 | 3359.5 / 35891 ms | 538.5 ms | Conflict, injection, definition and write-request rubric misses |
| Gemini 3.5 Flash Lite | 8/10 | 1046.5 / 1656 ms | 961 ms | Definition and write-request rubric misses |
| Gemini 3.8 Flash | 6/10 | 4242.5 / 7844 ms | 4195.5 ms | Four HTTP 429s; successful-only latency excludes these errors |

Flash Lite's median full response was about 3.2× faster than Qwen on this rubric, while Qwen's first token arrived earlier. A first token is not a validated answer. No application UI displays partial citation claims as verified. The ten-case sample is descriptive and insufficient for broad model-quality conclusions. Malformed/unsupported output is separately rejected by application tests, and provider outage fallback is exercised with deterministic failure injection.

At the [researched paid rates](https://ai.google.dev/gemini-api/docs/pricing?frmapp=yes), the ten Flash Lite calls total approximately **$0.001604**, with median approximately **$0.000159/request**. The six successful Flash calls total approximately **$0.005980**, with median approximately **$0.000801/request** using the October promotional rates. These are token-based estimates from returned usage, not invoices; actual account tier/billing was not established. Qwen has no per-request provider bill; energy/hardware cost was not measured. No search, context caching, file storage or other provider tools were used.

The actual Java Gemini adapter then answered two fixed fictional requests: general **1691 ms** (51 output tokens) and grounded **793 ms** (48 output tokens, one validated citation). This confirms transport/schema/validation integration, not private-document authorization or a statistically meaningful latency distribution. Its isolated test supplies the gate for fictional data; the running app remains cloud-disabled.

## Coverage limits

- Native/table/scanned/DigiLocker-associated extraction, general chat, grounded citation, review, repeated requests and provider rate limiting were measured directly.
- Complex explanation, ambiguous model-selected cell linking, source-heavy conflict handling and malformed-provider behavior have correctness tests/rubric evidence, but no full before/after end-to-end latency distribution. No such performance is inferred.
- HTTP queueing, cold OS state, provider hardware memory and an actual private paid-account workflow were not independently measured.
- Outage/cancellation/permission/status tests validate bounded behavior and no authority changes; a real prolonged Google outage was not manufactured.
- Local model absence preserves deterministic/manual behavior, and cloud is never selected automatically for sensitive input. No 2× speedup is claimed for uncached local inference or first-time document extraction.
