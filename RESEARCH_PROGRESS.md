# Foliolet PS32 verified-source implementation checkpoint

## Source and safety boundary — 16 October 2026

- Verified remote source: `feature/digilocker-assisted-intake` at `6db30e1520211b0dae88c8b47200a9ed1b6089c7`.
- Direct parent: `8e6671003c090dc958ce718afa12484c5e47299b`.
- Source tree: `920e84b1530906b8117f859bff7b99b7aae32b7d`.
- Sole working branch: `feature/ps32-verified-hardening-20261016-6db30e1`, created from that exact commit.
- `main`, `cf`, and the original DigiLocker branch must remain untouched. No force-push, production-state changes, secret changes, or migrations against user data.
- Prior recovery package remains preserved byte-for-byte in the supplied archive; its 101 tests describe the earlier independent laboratory, not this application.

## Preflight status

Remote ref/parent/tree reads and isolated branch creation succeeded through the connected GitHub API. The local container cannot resolve GitHub, Maven Central, or PyPI. Connected browser access is unavailable. No complete local clone, application source edit, build, OCR benchmark, security test, or workflow rehearsal has yet succeeded in this run.

Next action: test a narrowly scoped GitHub Actions checkout on THIS branch, with read-only contents permissions, no repository secrets, no deployment, and credentials not persisted. Retrieve a source Git bundle through the workflow artifact connector if available, then establish the real local working tree and baseline before application edits.

The original failure PDFs are not present in the supplied recovery ZIP. Specific original-PDF reproduction remains NOT TESTED. No claim of issuer verification or demo readiness is made.

## Test prerequisites

Actual Foliolet Java/Maven and Python dependencies, Node/Solidity tooling, OCR engine, isolated PostgreSQL/Ganache where needed. The local container has Git, Java, Node and Tesseract, but no Maven executable/cache was found and external dependency resolution currently fails.

## Actual application work — 16 October 2026, 14:45 UTC

Source access is now resolved: GitHub Actions run 38915644686 cloned the isolated branch, verified ancestry and writable clean source, and exported a SHA256-verified Git bundle. The complete repository is cloned locally at the same branch. No alternative branch was used.

Baseline run 38916059463 / commit bd778cb9606f20eec77f1a07544bab7568321984: 93 Java, 72 Django, 11 Linux watcher and 22 Node tests passed; real disposable-EVM contract regression passed. Model inference, Windows and physical NFC were not exercised. The local full baseline attempt was terminated by the container call deadline before all Spring contexts completed; it is not a second complete pass.

Implemented locally: PDFBox native token geometry with exact text mapping; bounded source-layout suggestions independent of Ollama; explicit header selection, duplicate-scope abstention, per-word OCR review gating, exact hash/version/span binding, sanitized rejection diagnostics; malformed/nonfinite TSV rejection. Existing model-output validation remains strict; Ask Foli remains local-model based.

Focused application tests: 26 passed (12 source-layout, 1 real PDFBox, 3 TSV validation, 10 existing strict fact-validation). First run exposed an invalid-date exception; fixed and rerun. This is not a real-world accuracy claim. Original failure PDFs remain unavailable.

Next: whole application regression, actual Tesseract before/after corpus, licensed real data, alternative-engine feasibility, whole-repository risk audit and end-to-end gates. All suggestions remain holder-reviewed; issuer stays NOT_VERIFIED.
