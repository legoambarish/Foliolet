# Foli phase 4 — private Ask Foli interface

Added Ask Foli beside Documents, Shared and First-seen in the authenticated native Django navigation. The page uses the existing Foliolet typography, light/dark tokens and controls, with a responsive source library, rounded composer/up-arrow send button, reading progress/Stop, retry, coverage panel, structured fine-print cards and a source viewer with exact-text highlights and authenticated PNG previews.

The proxy uses only current server-side session credentials and numeric loopback, with no environment proxies, redirects, stub credentials, arbitrary paths or URLs. Job mutations require Django CSRF. Source parameters are typed and size-bounded. The Foli page has a stricter self-only CSP; its request paths are suppressed from development access logs. No receiver URLconf, receiver static allowlist, share behavior or public assets were changed.

Model and document strings are rendered with DOM text nodes. The small markdown subset accepts no HTML, images, active links or model-generated URLs. Changing source clears conversation context; forgetting also removes server jobs/cache for the current user. No source/chat history is persisted in browser storage. Authorization loss clears visible source/conversation data, and restored back/forward pages reload to reauthorize.

Measured gates:

- 13 Django Foli tests pass, zero failures; CSRF, local confinement, bounds, errors, redirect rejection and receiver negatives included.
- Real Edge 155 / Playwright 1.62.1 browser run: 18 checks pass, zero JavaScript exceptions and zero external browser requests.
- Real local inference, 125-page source coverage, fee answer/citation, exact highlighted excerpt, original PDF rendering, 40 fine-print cards including page 125, category filter, cancellation and scanned-page OCR were exercised through the UI.
- Explicitly synthetic UI response tests verify hostile model HTML/links, missing-model state and authorization-loss clearing. These are browser trust/state tests, not claims that the live runtime was missing or the real session revoked.
- 390px mobile layout has no horizontal overflow; theme switching uses the existing controls. Screenshots are real browser captures under ignored `.local-data/foli/ui-*.png`.

The first two UI harness attempts found fixture setup mistakes (registration returns text; the scan fixture is named `scan.pdf`); both were corrected, and the failed logs retained. A screenshot captured during the existing 280ms theme transition was replaced after adding a computed-colour/transition-settled check. No product theme code was changed.

Responses are returned after source verification with progress/cancellation rather than token streaming. This avoids displaying provisional claims as verified. The source viewer highlights extracted text; it does not claim pixel-perfect PDF/OCR bounding-box alignment.
