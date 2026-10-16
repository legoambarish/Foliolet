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
