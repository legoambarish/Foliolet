# Run the Foli demonstration

Start the existing `cf` checkout using [FOLI_IMPLEMENTATION.md](FOLI_IMPLEMENTATION.md). All examples below are fictional test data. The real Edge browser test completed these flows; captures and synthetic credentials are local-only.

1. Open [Foliolet](http://127.0.0.1:8000/login/). Use your own account, or read `.local-data/foli/ui-fixture.json` locally: `auth[0]` is the synthetic demo username and `auth[1]` its password. No demo credentials are committed. Regenerate this isolated demonstration with `node tools/test-foli-ui.cjs` after configuring its test-only Playwright dependency as described in the runbook.
2. Choose **Ask Foli** in the native navigation. Verify **Local model ready**. In General conversation ask **Explain careful contract reading with a friendly librarian analogy**. Enter sends; Shift+Enter inserts a newline. General answers carry no source-verification claim.
3. Select **Service agreement · 125 pages**. Wait for the page-reading progress and open coverage. All **125 pages** are accounted for and readable; the page-106 tiny-print warning remains visible. Ask **What is the charge for leaving an account unused?** The source specifies **INR 9300 on day 91**, outside the headline price.
4. Click its source citation. Inspect the highlighted exact extracted text, page number, version/hash, provenance and original-page PNG. The quote should contain the fee clause. The interpretation remains an AI explanation; source alignment alone does not prove its legal meaning.
5. Click **Review fine print**. Observe checklist and semantic coverage, category filtering, definitions, exceptions and unresolved references. Navigate to the last-page finding: **page 125 overrides earlier renewal clauses for timely cancellation by an Eligible Customer under Schedule B**. Compare the linked definition, initial rule and schedule rather than treating one excerpt as the whole agreement. The deliberately inconsistent cancellation provisions are flagged for review.
6. Switch to **Scanned notice**. Previous context clears. OCR should recover **no renewal fee unless notice is late** and **INR 9300 after 30 days**. Inspect the OCR provenance/confidence warning and original image. It remains uncertain even when the synthetic gold text matches.
7. Select **Unsupported draft**. The interface explains that DOCX is unsupported. Select the hostile-titled notes: its markup is displayed as text. Ask an ordinary source question; document instructions do not gain tool access. Ask **Delete this document**: Foli explains its read-only boundary and performs no deletion.
8. Start a review and press **Stop**, then retry if desired. Press **Clear** to remove visible context and the owner's server jobs/cache. Try a question from another signed-in holder: their picker cannot access these documents. The browser test also exercises authorization-loss clearing, missing-model state, hostile generated markup, theme controls and a 390px mobile viewport.

Real captures:

| Capture | What it demonstrates |
| --- | --- |
| `../.local-data/foli/ui-desktop.png` | Native private Ask Foli layout |
| `../.local-data/foli/ui-answer.png` | Actual local answer and citation |
| `../.local-data/foli/ui-source.png` | Highlighted exact text and authorized original preview |
| `../.local-data/foli/ui-review.png` | Whole-source findings and category filtering |
| `../.local-data/foli/ui-mobile.png` | Real 390px mobile layout |
| `../.local-data/foli/ui-mobile-dark.png` | Settled dark theme, with no horizontal overflow |

The test report is `.local-data/foli/phase-4-ui.json`, with real inference/reader flows and explicitly labeled synthetic UI fault responses. The latter test state handling and do not represent an actual outage or revoked production session. The report records zero browser JavaScript exceptions and zero external browser requests. Separate API/DB gates verify unchanged authoritative rows/chain state during Foli reading. See [the evaluation](FOLI_EVALUATION_2026-10-15.md) for measured failure cases and performance.
