# Phase 4: implemented with external and hardware gaps

Implemented uploaded XML, mock and gated Setu sandbox provider interfaces; consent/poll/cancel/timeout overlay; secure XML parsing and scoped externally pinned signature validation for a narrow explicit test profile. Mock/unsigned sources remain SELF_ASSERTED, unsupported signatures/schemas remain UNKNOWN, and holder review never creates native authority. Raw fetched bytes are not retained by default.

Restricted public-only Django settings expose only discovery, public reader, share/status and callback routes. Local public preview was tested; private routes return 404. The disabled-by-default tunnel manager requires explicit operator exposure opt-in and monitors live grants. No tunnel was exposed. Cloudflare sees disclosed facts; URL-fragment encryption was cut. Cancellation clears the local session but Setu remote session revocation has not been implemented or tested.

Actual mock/XML cryptography, XXE refusal, ownership/cancellation, public routing and browser overlay tests pass. No authentic provider sample, authorized Setu access or physical NFC hardware was available. Real issuer XML schema/authority onboarding and physical tapping remain NOT TESTED. Native reset, warm-up, rehearsal, judge FAQ, labeled backup recording script and offline checklist exist. No backup video was recorded.
