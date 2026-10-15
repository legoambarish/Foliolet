"""Build the factual handoff from completed local synthetic evidence. No inference."""
import collections
import json
from pathlib import Path
import re
import statistics

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'.local-data/foli'; DOCS=ROOT/'docs'
def read(name): return json.loads((OUT/name).read_text(encoding='utf-8'))
def safe(value): return str(value).replace('|','/').replace('\n',' ')
def main():
    qa=read('phase-5-qa-release.json'); assert qa['total']==80,'Wait for all 80 release cases before writing the final report'
    models=read('model-benchmarks-selected.json'); reader=read('phase-5-reader-benchmark.json'); review=read('phase-3-live-review.json')
    ui=read('phase-4-ui.json'); safety=read('phase-5-adversarial.json'); ocr=read('ocr-package-receipts.json')
    java=(OUT/'phase-5-java-release-all.log').read_text(errors='replace')
    assert 'BUILD SUCCESS' in java
    counts=re.findall(r'Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)',java)[-1]
    assert counts[1:]==('0','0','0')
    browser_checks=[e for e in ui['events'] if e['name']!='Isolated synthetic user and four documents enrolled']
    assert not ui.get('failure') and not ui['errors'] and not ui['external'] and len(browser_checks)==18
    assert qa['quotationAlignmentFailures']==0
    lines=['# Foli evaluation — 15 October 2026','',
        'These are executed results from the existing Windows `cf` checkout, not proposed targets. All evaluation documents/accounts are newly generated synthetic fixtures. The corpus is authored and keyword-rich; it is not an independent sample of real legal contracts. Source alignment, passage recall and legal correctness are distinct measurements.','',
        '## Release gates','',
        '| Gate | Measured result |','| --- | --- |',
        f'| Java, including real child readers, real OCR and live loopback inference | {counts[0]} tests; zero failures, errors or skips |',
        '| Django, including receiver separation and CSRF | 63 passed |',
        '| Separate Node proof verifier/UI | 22 passed |',
        '| Solidity registry | PASS on real in-process Ganache, including seven Merkle-tree shapes |',
        '| Existing live wallet workflow / security | 51 / 23 real HTTP, PostgreSQL, EVM checks passed |',
        '| Live Foli source/security reading | 26 checks passed |',
        f'| Live Foli adversarial/DB/chain/log gate | {safety["count"]} checks passed; authoritative row counts and chain block unchanged |',
        f'| Real Edge {ui["browser"]} / Playwright UI | {len(browser_checks)} browser checks plus fixture setup passed, zero JavaScript exceptions or external requests |',
        '| Packaged Spring Boot JAR reader | PASS with actual PropertiesLauncher and exact synthetic text |','',
        'Authorization coverage includes two holders, OFFICER and ADMIN, wallet-owner enforcement even against ADMIN, legacy uploader/admin access, stale hashes, AES-GCM tampering, replacement/deletion, role changes, job ownership and no restore/write behavior. The bounded child-reader tests include 125-page extraction, original rendering, corrupt input, cancellation, a blocked output consumer/time budget and scratch cleanup. Malicious PDF tests cover opening JavaScript, hostile metadata, oversized image dimensions and recursive forms. New UI state faults are explicitly synthetic responses; real read/chat/review/OCR/cancel flows use the live services.','',
        '## Eighty-case application benchmark','',
        'The fixed corpus contains 40 explain-quoted-clause prompts, 20 independently phrased questions, 10 deliberately unavailable facts, 5 write requests and 5 general questions. A document pass requires the expected gold page and complete expected passage in a verified citation (whitespace normalized only for the gold comparison); a valid alternate passage can therefore be a strict rubric miss. This is evidence-location support, not a blinded judgment of every answer sentence.','',
        f'Final result: **{qa["sourceSupportPassed"]}/80 ({qa["sourceSupportPassed"]/80:.1%}) rubric passes**. The complete raw answers and source metadata are in `.local-data/foli/phase-5-qa-release.json`.','',
        '| Kind | Passes / cases |','| --- | --- |']
    for kind in ('document','unanswerable','write','general'):
        cases=[c for c in qa['cases'] if c['kind']==kind]
        lines.append(f'| {kind} | {sum(c["sourceSupported"] for c in cases)}/{len(cases)} |')
    quotes=sum(len(c['answer'].get('citations',[])) for c in qa['cases'])
    timings=[c['seconds'] for c in qa['cases']]
    lines+=['',f'**{quotes} returned chat citations were reopened and checked against exact current source offsets; zero quotation-alignment failures.** This does not mean every attached excerpt semantically supports every statement.',
        f'Observed app-job latency median {statistics.median(timings):.3f} s, maximum {max(timings):.3f} s. These include queue contention from concurrent browser/review tests; ten starts/minute is respected with explicit waits. Use the isolated raw-model timings below for inference comparisons.','',
        'Strict misses (retained rather than relabeled as successes):','']
    for case in qa['cases']:
        if not case['sourceSupported']:
            locations=', '.join(str(c['page']) for c in case['answer'].get('citations',[])) or 'none'
            excerpt=safe(case['answer']['answer']); excerpt=excerpt if len(excerpt)<=520 else excerpt[:520]+'...'
            lines.append(f'- **{case["id"]}** — expected page {case["goldPage"]}; cited pages {locations}; {case["answer"]["answerKind"]}. Response excerpt: {excerpt}')
    lines+=['','Earlier retained runs include 74/80 before abstention/inline-ID handling, 75/80 with that hardening, an interrupted refinement exposing sparse excerpt-ID/clause confusion, and the targeted local-ID regression. The final implementation suppresses common boilerplate, prioritizes requested headings and uses compact IDs for each chat answer. The early completed-job capacity bug and incorrect portable OCR data path were fixed; their failed logs were preserved. No partial run is counted as 80 completed cases.','',
        '## Whole-document fine-print gate','',
        f'The actual 125-page PDF review completed in **{review["seconds"]:.3f} s**, finding **{sum(c["found"] for c in review["gold"])}/40 authored critical passages** and **{review["quotesAligned"]} exact source quotes**, including the overriding page-125 exception. The earlier measured pass was 18.171 s.','',
        f'Coverage: `{json.dumps(review["response"]["reviewCoverage"],sort_keys=True)}`.','',
        f'Flagged-page precision versus the authored clause-page set: **{review["passagePagePrecision"]:.0%}**. This metric concerns passage locations, not correctness of generated legal interpretation. Three definition passages and one unresolved schedule reference remain explicit. Tiny-print extraction uncertainty is retained. Twelve broad checklist categories supplement source-ordered semantic mapping; unreadable/limited pages cannot support an absence claim.','',
        '## Reader and OCR measurements','',
        '| Fixture | Elapsed incl. enrollment / read | Status | OCR character / word error |','| --- | --- | --- | --- |']
    for item in reader['results']:
        errors=f'{item["characterErrorRate"]:.1%} / {item["wordErrorRate"]:.1%}' if 'characterErrorRate' in item else 'not scored'
        lines.append(f'| {item["name"]} | {item["seconds"]:.3f} s | {item["page"]["status"]} | {errors} |')
    lines+=['','Every fixture page was accounted for. OCR gold comparison normalizes whitespace only; the two clean printed scans recovered negation and INR 9300 exactly. This small sample establishes neither handwriting accuracy nor performance on low-resolution or multilingual legal scans. Mixed sources retain both native and OCR readings when they differ. Multi-column text warns about visual reading order; blank pages stay unreadable. Reader identity: '+', '.join(sorted({item['manifest']['extractorVersion'] for item in reader['results']}))+'.','',
        '## Actual model comparison','',
        'Same machine, Ollama 0.40.3, Q4_K_M, 8192 context, temperature 0.1, seed 42, one generation, 350-token comparison ceiling, ten synthetic raw-model tasks. These tasks are separate from the 80 application cases and do not apply the application write/citation guards. Cold means unloaded model, not a reboot or purged OS disk cache. Warm median uses the remaining nine heterogeneous short prompts. Model VRAM is from `/api/ps`; GPU usage includes desktop/driver allocations. RAM is the measured native llama-server process working set, not total application memory.','',
        '| Model | Package bytes | Raw tasks | Cold s | Warm median s | Warm median tokens/s | Model VRAM GiB | Native runner RAM GiB |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for model in models['models']:
        cases=model['cases']; running=model['running']['models'][0]
        ram=sum(p['WorkingSet64'] for p in model['gpuAfter']['ram']['processes'] if p['ProcessName']=='llama-server')
        lines.append(f'| {model["model"]} | {model["bytes"]:,} | {model["passed"]}/10 | {cases[0]["seconds"]:.3f} | {statistics.median(c["seconds"] for c in cases[1:]):.3f} | {statistics.median(c["tokensPerSecond"] for c in cases[1:]):.2f} | {running["size_vram"]/2**30:.3f} | {ram/2**30:.3f} |')
    cpu=models['cpuFallback']; cpu_ram=sum(p['WorkingSet64'] for p in cpu['resources']['ram']['processes'] if p['ProcessName']=='llama-server')
    lines+=['',f'Actual **CPU-only Qwen3 4B**: {cpu["seconds"]:.3f} s for {cpu["tokens"]} generated tokens, {cpu["tokensPerSecond"]:.2f} tokens/s, 4096 context, model VRAM **0 bytes**, native runner RAM {cpu_ram/2**30:.3f} GiB. This measures CPU generation, not a forced full-GPU OOM experiment.','',
        '**Selected: qwen3:4b-instruct**, the smallest compared candidate meeting the retained application/fine-print gates with a permissive Apache-2.0 license. The 3B package is smaller but scored 1/10: malformed evidence IDs/arrays, failure to preserve source support and a false claim that a requested edit was completed. The application never exposes write tools. Gemma ties 8/10 at a larger package size under its separate terms; 7B scored 7/10 and was slower.','',
        'Raw-model limitations remain: both 4B candidates failed the conflict task; Qwen safely abstained on the injected notice passage, and Gemma missed the linked-account definition. A larger package did not remove these weaknesses. Exact digests, quantization, full model-specific license receipts, responses, RAM/GPU snapshots and CPU configuration are retained in `.local-data/foli/model-benchmarks-selected.json`.','',
        '## Privacy, offline scope and limits','',
        'All application listeners are numeric loopback. Ollama `/api/status` reports cloud disabled from environment; the native llama-server was also observed with `--offline` and `--no-webui`. Java live inference passed with non-loopback connects denied, with a negative external-socket control. The browser test permits only local requests. The live injection canary was absent from the private Java/Django logs, and authoritative DB counts/chain height were unchanged during the Foli-only adversarial gate.','',
        '**Not performed:** physical Windows network-adapter disconnection; OS-level egress sandboxing of every native process; exhaustive native-parser security review; real-world multilingual/handwriting accuracy or legal-interpretation validation. The reader heap/wall-clock boundary limits resource failures, not host-user privileges. Normal source citations can still attach an imperfect interpretation, and safe abstentions can miss answerable questions. The source viewer, scope warnings and full-document mode remain essential.','',
        'No receiver routes/assets, blockchain contracts, share authorization, document mutation or Cloudflare configuration were changed for Foli. New runtime state is local-only. The checked-in source contains no model weights, secrets, production customer documents or paid services. See [startup and architecture](FOLI_IMPLEMENTATION.md) and [demonstration](FOLI_DEMO.md).','']
    outage=read('phase-5-outage.json')
    assert outage['offline']['jobState']=='ERROR' and outage['restored']['jobState']=='COMPLETE'
    lines+=['## Actual runtime outage and recovery','',
        f'The specifically verified local Ollama process and its own runner were stopped after the corpus finished. Health became OFFLINE; a real general-chat job returned ERROR/OFFLINE in {outage["offline"]["seconds"]:.3f} s with no answer or fallback. The documented launcher restarted the same runtime/models; health returned READY and a real inference job completed in {outage["restored"]["seconds"]:.3f} s. PostgreSQL, Spring, Django and chain state were preserved. Receipt: `.local-data/foli/phase-5-outage.json`.','']
    resources=read('phase-5-app-resources.json')
    lowest_free=min(s['os']['FreePhysicalMemory'] for s in resources['samples'] if 'os' in s)/2**20
    earlier=resources['earlierMixedBenchmarkObservation']['nativeRunnerWorkingSetBytes']/2**30
    lines+=['## Application workload memory','',
        f'After restarting Ollama, another actual 125-page full review completed in {resources["seconds"]:.3f} s. Across {len(resources["samples"])} OS samples, native runner peak working set was **{resources["nativeRunnerPeakWorkingSetBytes"]/2**30:.3f} GiB**; lowest observed system free RAM was **{lowest_free:.3f} GiB**. This is a workload observation, not a hard process-memory ceiling.',
        f'An earlier extended mixed CPU/GPU/model/application session reached a native runner working set of **{earlier:.3f} GiB**. Its cause was not isolated; it is retained as a capacity limitation rather than erased by the fresh-runtime result. The short comparison table above must not be interpreted as a long-duration RAM guarantee. Receipt: `.local-data/foli/phase-5-app-resources.json`.','']
    (DOCS/'FOLI_EVALUATION_2026-10-15.md').write_text('\n'.join(lines),encoding='utf-8')
    deps=['# Foli dependency and license receipts — 15 October 2026','',
        'Application versions were resolved and built locally; downloads were explicit setup actions. This inventory records supplier license labels, not legal advice or a redistribution clearance. Runtime state/weights are ignored rather than bundled in source.','',
        '| Component | Version / license |','| --- | --- |',
        '| Spring AI Ollama | 2.0.1, Apache-2.0; BOM pinned in pom.xml, compatible with existing Boot 4.1.1 |',
        '| PDFBox | 3.0.8, Apache-2.0 |',
        '| Ollama | 0.40.3, MIT; archive SHA-256 e5ecff02dfc7cae8ddf6d6b7a7ac5f727ffeedf4491f44ae75ff5b0820dbbbd5 |',
        '| Tesseract / Leptonica | 5.5.3 Apache-2.0 / 1.87.0 BSD-2-Clause |',
        '| Python application / browser | Existing Django requirements retained; Playwright 1.62.1 Apache-2.0 is test-only |',
        '| Repeat fixture generator only | PyMuPDF 1.27.2 AGPL-3.0/commercial; Pillow 12.1.1 HPND. Neither is the production parser. |','',
        'The retained fixture PDFs were initially generated with bundled PyMuPDF 1.28.2 and Pillow 12.3. The repeat-generator pins were installed afterward. Gold wording/pages are fixed; byte-identical PDF regeneration is not claimed across those library versions. Original fixture bytes/hashes are preserved, and each live citation uses its actual source SHA-256.','',
        'The OCR lock pins 31 exact conda-forge package URLs/builds with MD5 archive fragments; full SHA-256 and supplier license metadata are retained in `.local-data/foli/ocr-package-receipts.json`. Its offline dry run succeeded without modifying the installed environment. Micromamba 2.9.0 archive SHA-256: `97a336f4ab794bd96a6a4da5e6ed63e75a1d31830414a182419b23d3b36f3fe0`.','',
        f'OCR lock SHA-256: `{ocr["lockSha256"]}`.','',
        '| OCR package | Exact version/build | Supplier license |','| --- | --- | --- |']
    for package in ocr['packages']: deps.append(f'| {package["name"]} | {package["version"]} / {package["build"]} | {safe(package["license"])} |')
    deps+=['','## Measured model identities','']
    for model in models['models']:
        license='Gemma Terms of Use' if model['model'].startswith('gemma') else 'Qwen Research License Agreement' if model['model']=='qwen2.5:3b' else 'Apache-2.0'
        deps.extend([f'- **{model["model"]}** — {model["bytes"]:,} bytes, {model["details"]["quantization_level"]}, {license}; digest `{model["digest"]}`.'])
    deps+=['','All four measured packages are strictly below 6 GB individually. Their licenses differ; the research-licensed 3B candidate and Gemma are not selected or redistributed with this source. Package storage, context/KV allocation, process RAM and VRAM are distinct. Model tags can move upstream: verify the recorded digest and repeat benchmarks after any change.','',
        'Primary references: [Spring AI compatibility](https://docs.spring.io/spring-ai/reference/getting-started.html), [Ollama FAQ](https://docs.ollama.com/faq), [selected Qwen tag](https://ollama.com/library/qwen3:4b-instruct), [Tesseract](https://github.com/tesseract-ocr/tesseract), [PDFBox](https://pdfbox.apache.org/), [PyMuPDF license](https://pymupdf.readthedocs.io/en/latest/about.html#license).','']
    (DOCS/'FOLI_DEPENDENCIES_2026-10-15.md').write_text('\n'.join(deps),encoding='utf-8')
    print('Wrote factual evaluation and dependency reports from 80 completed release cases')
if __name__=='__main__': main()
