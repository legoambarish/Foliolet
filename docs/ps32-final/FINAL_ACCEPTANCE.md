# Final acceptance — Foliolet PS32

**Assessment:** 16 October 2026 UTC. **Release boundary:** controlled local, fictional-data demonstration; not production or universal issuer verification.

This addendum resolves the pending states in earlier reports without erasing their failed runs. The final tested application commit is **`998ffe7fc33777891f36eeaa7118939b3e8b4dd7`**. Subsequent report, evidence, workflow-cleanup and archive commits do not change application behavior. The required source baseline remains `db55c2c6c1209e567713fa9ab08c5441bd55bc86`.

## 1. Final executed acceptance

| Gate | Actual result | Exact evidence |
|---|---|---|
| Java regression | **131 tests, 0 failures, 0 errors, 0 skipped** | [Run 38948026728](https://github.com/legoambarish/Foliolet/actions/runs/38948026728), application `998ffe7…` |
| Django regression, Linux | **105 tests, all passed** | Same run; actual Django output inspected |
| Independent Node verifier | **22 tests, all passed** | Same run; genuine/tampered/pin-change cases |
| Solidity integration | Passed authorization, immutable roots, unsupported assurance, atomic supersession, revocation and seven independent Merkle shapes | Same run; no fabricated assertion count |
| Full-stack lifecycle | **51 checks passed** | [Run 38948026733](https://github.com/legoambarish/Foliolet/actions/runs/38948026733), application `998ffe7…` |
| Live authorization/proof attacks | **23 checks passed** | Same full-stack run |
| Actual OCR/review-to-proof browser | **5 acceptance checks passed** | Same run, real Chromium and source-review UI |
| Missing-service/interrupted-job cases | **12 checks passed**, plus three CSV fallback checks | Same run; real missing engines and explicit local test doubles distinguished |
| Watcher / complementary OCR / QR helpers | **5 / 6 / 3 tests passed**, respectively | Same run; exact suite outputs retained |
| Signature browser flow | **3 cases passed:** unsigned, genuinely signed but issuer-untrusted, tampered | Same run; original source hash matched; no external browser document requests or JS errors |
| Real dependency interruption/restart | **17 checks passed**, including the signature flow phase | Same run; actual PostgreSQL container, EVM process and packaged backend stopped/restarted with retained state |
| Windows Django | **105 discovered/run count, 1 platform-specific skip, remainder passed** | [Run 38946428108](https://github.com/legoambarish/Foliolet/actions/runs/38946428108), Windows-2025; relevant Django code unchanged afterward |
| Windows launchers | Start/stop PowerShell AST parsing and new-branch/heap guard checks passed | Same Windows run; not a complete Windows PostgreSQL/EVM startup |

These categories overlap and must not be added into an invented single total. Relative to the original baseline, the Java and Django suites contain **54 additional regression tests** (23 Java and 31 Django). The six initially failing source-association cases and valid controls were preserved and later passed.

Full-stack execution uses the actual Django → Spring → PostgreSQL → encrypted vault → Ganache/Web3j → independent-verifier workflow. It does not replace the application with a mock laboratory. Original user runtime state was never used.

## 2. Final dependency results

The final Java override is **Bouncy Castle 1.85**, superseding the intermediate 1.84 mentioned in earlier reports. The remaining 1.84 matches were [GHSA-9pwp-9qqc-pr26](https://github.com/advisories/GHSA-9pwp-9qqc-pr26) and [GHSA-qp49-qgx5-5m26](https://github.com/advisories/GHSA-qp49-qgx5-5m26); the vendor identifies 1.85 as the fixed release for the relevant certificate/signature issues. The tested wallet uses its existing cryptographic format; the patch did not introduce a new credential protocol.

[Release evidence run 38948420909](https://github.com/legoambarish/Foliolet/actions/runs/38948420909), source `5bd7aa077a093c79a483fabf9b18755437100a30`, resolved and queried **144 Maven runtime dependency coordinates** against OSV: **zero advisory matches**. The resolved list confirms BC 1.85. The same job verified baseline ancestry, `git diff --check` and hashed the source archive/bundle. Zero feed matches is not proof that no vulnerability exists.

The final Python application audit covered **52 installed dependency records with zero known advisory matches** after Django 6.1.2 and urllib3 2.8.0. That Python environment was unchanged by the later Java-only BC patch. The Java security set also includes Tomcat 11.0.26, Jackson 2.21.7/3.1.7, OkHttp 4.12.0 and Okio 3.6.0.

**Unresolved:** the Spring-side npm/Ganache dependency tree still has **39 reported advisories: 2 low, 9 moderate, 23 high and 5 critical**. Root npm was clean. Do not call the entire supply chain clean. Ganache's missing native uWS binary falls back to its Node implementation; this passes the demo but does not establish production suitability. Blind forced downgrades were rejected.

## 3. Actual retained-state recovery

The final run proves that an unavailable database or chain does not become a verified result, and that the same proof succeeds when the original state returns. It checks signing/vault key hashes, byte-exact original recovery and holder-session continuity. The backend restart did not regenerate keys, reset the chain or create a replacement credential to manufacture success.

Final single-run observations:

| Observation | Measured value |
|---|---:|
| Database-outage verification failure response | 0.03547 s |
| EVM-outage verification failure response | 0.00741 s |
| Packaged backend restart to network endpoint | 4.578 s |

An earlier database interruption took 30.012 s; a configurable five-second Hikari connection-acquisition bound was introduced. The final 35-ms outcome is the observed immediate failure path, **not** a proven 846-fold speedup, a five-second worst-case guarantee or a production latency percentile. Different failure timing can exercise different pool paths.

## 4. Document evaluation retained without score inflation

The controlled comparison in [run 38940026280](https://github.com/legoambarish/Foliolet/actions/runs/38940026280) used the exact baseline and then-repaired extraction code with identical fictional corpus bytes and engine conditions. Later privacy/dependency changes were regression/E2E tested but the full paired OCR corpus was not silently relabelled as a measurement at the final commit.

Both revisions produced 168 correct unique field/value pairs from 169 labelled facts, 170 suggestions, zero incorrect automatic suggestions and two incorrect review suggestions. Recall including review suggestions was **99.4083%**; suggestion precision **98.8235%**; all **769/769** support fragments matched source text. These are synthetic-corpus results, not issuer authenticity or general real-world accuracy.

Eight licensed public CORD receipts completed. Six fixed test rows were held out from the start. Four of six grand totals were correct normalized decimals, a fifth had the correct source literal but unsupported currency normalization, and one selected an identifier instead of a total. All emitted suggestions required review. No held-out tuning was performed. Exact ground-truth provenance and per-case values are in [EVIDENCE.md](EVIDENCE.md) and the compact JSON record.

## 5. Real local AI: negative result remains part of delivery

The actual `qwen3:4b-instruct` model ran under Ollama 0.40.5 after public download, inside an OS network namespace containing only loopback. Model digest: `0edcdef34593bde9c1be0ec7dffb75b2dd58bffab89c875f343bf6cfe8daf188`; quantization Q4_K_M; stored model size 2,498,927,792 bytes. No original user model store or private document was used.

[Extended run 38943519647](https://github.com/legoambarish/Foliolet/actions/runs/38943519647) passed **5/10 strict answer-and-citation cases**. Several plausible answers cited the wrong or excessive evidence. The tested injection canary stayed suppressed, but that is not a general injection-immunity claim. The rubric was not weakened or rerun until green.

A separate actual `FoliLocalModel`/Spring-AI integration passed **3/3 focused cases**: grounded answer, missing-information response and read-only refusal. Observed model responses were roughly 16–33 seconds on the tested CPU environment. Keep AI optional and outside the critical presentation path. The model workflow's failed quality gate is intentional retained evidence; not every historical workflow is green.

The `time -v` memory output in that experiment measures the Python client, not the Ollama server. It must not be used to claim a 23-MiB model footprint. No full concurrent OCR-plus-model production memory benchmark was established.

## 6. Safety and branch preservation

The temporary write-enabled patch transport was deleted at **`d2d5fa7415cb4a0d11ed761bb6cf0ac9cec6d069`**. Remaining delivery workflows do not need repository write permission. Private runtime data, keys, tokens, original user documents and model weights are excluded from the report package.

At final reference inspection, the required source branch still pointed to **`db55c2c6c1209e567713fa9ab08c5441bd55bc86`**. The observed other protected refs were `main` → `6e39e21cd56bdc8b912a4790baf0a42619e7b302` and `cf` → `b053b324e87d4a90f4d0151d3f7e7077759a89c5`. No mutation was directed at those branches. Their final observation is not misrepresented as an independently recorded initial baseline for every ref.

No credential encoding, Merkle canonicalization, stored encryption key or original chain state was silently changed. Legacy session rewriting is explicit and compatible. Earlier research and failed results remain preserved.

## 7. Release conclusion and exclusions

The tested core and new trust/privacy features are suitable for a **controlled local PS32 demonstration after an actual-machine rehearsal**. The complete A–L index is [README.md](README.md), and the 33-question defense and startup/demo instructions are committed alongside this report.

Not established: production readiness; genuine issuer authority; general Indian academic-document accuracy; full macOS or Windows service lifecycle; actual NFC/mobile hardware; a live public Cloudflare tunnel; exhaustive PDF fuzzing; production concurrency/latency distributions; institutional API approval; or exact prebuilt-code eligibility. Those are explicit limits, not hidden passes. The goal is a technically credible contender; no evidence can guarantee the judging outcome.
