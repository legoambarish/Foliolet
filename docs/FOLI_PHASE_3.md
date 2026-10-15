# Foli phase 3 — whole-document fine-print review

Implemented a separate review mode. Every readable source page/chunk receives a deterministic checklist scan, followed in source order by bounded semantic map batches. Findings retain exact page/offset citations, qualifier wording, related definitions and clause/section/schedule references. Explicit conflicts and differing cancellation timing are flagged as possible tensions without deciding legal priority. A schedule mention is not presented as the schedule's actual contents when its heading cannot be located.

The reducer validates source IDs and categories, preserves checklist findings when a model batch fails, and reports successful semantic chunks separately from scanned/readable/unreadable pages. Model time, context and finding limits never become a claim that the document is clear of risks. Generated explanations are labeled interpretation; checklist guides are reading prompts.

Real gate on this machine (2026-10-15):

- 15 focused Q&A/review tests passed (10 Q&A + 5 review), zero failures/errors/skips. Independent labeled retrieval is now 60/60.
- Real Spring AI + Ollama full-source review of the 125-page synthetic PDF completed in **18.171 seconds**, with **125/125 semantic chunks**, **125/125 readable/accounted pages**, zero failed batches and all **40/40 gold critical-clause passages** found, including the final overriding exception.
- All **40 returned source quotes** matched their current authorized page offsets exactly.
- Flagged-page precision against the authored clause-page set is **100%** for this fixture. This is a passage-location metric, not model legal accuracy or generalization to arbitrary contracts.
- Three definition passages were identified. One referenced schedule heading remained unresolved and is shown as such.
- The tiny-print warning on the actual PDF remains visible; a complete semantic pass does not erase extraction uncertainty.

Evidence: ignored `.local-data/foli/phase-3-live-review.json`, its log, and `phase-3-tests-final.log`. Repeat with `python tools/test-foli-review.py` after generating/enrolling the synthetic reading fixture. The full 80-case chat benchmark continues into final regression; no negative results are discarded.

Limitations: checklist patterns are broad aids, and semantic interpretation can still miss or misunderstand scope, exceptions and contradictions. This local model has already failed some raw-model conflict tests. No legal opinion, enforceability decision or guarantee of comprehensive risk discovery is claimed.
