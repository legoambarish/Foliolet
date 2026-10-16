# PS32 research, differentiation and practical alternatives

Research checked on 16 October 2026. External findings below link to primary sources. Product choices and competitive judgments are explicitly engineering analysis, not claims that the organizer endorses Foliolet or that no competing product exists.

## 1. Official challenge and event boundaries

The organizer's [Hack Sprint tracks page](https://www.commudle.com/communities/cdn-commudle-developer-network/hackathons/hack-sprint/tracks) identifies PS32 as an open-ended Web3 problem around ownership, identity, trust and value, with innovation emphasized. It is not a requirement to build this particular document wallet. Sarvam/Gemini mandates observed in other problem statements must not be copied into PS32.

The [organizer's event overview](https://www.commudle.com/communities/cdn-commudle-developer-network/hackathons/hack-sprint) advertises a hybrid event, teams of 2–4 and a staged selection/mentoring process. Event metadata spans 17 October 2026, 09:00 IST through 18 October, 15:00 IST, while the description markets a 24-hour hackathon. Treat the published window and the description as distinct; neither establishes a submission deadline by inference. The exact current scoring weights, complete finalist rubric and eligibility of pre-existing code were not independently established. Existing-code disclosure must be honest; technical strength cannot override an organizer's eligibility rule.

The tracks page was intermittently unavailable during live retrieval; the successful organizer search/retrieval and previous preserved research were cross-checked. No invented numerical rubric or unpublished rule is used in this report.

**Analysis:** Foliolet fits the trust/privacy/ownership direction through selective disclosure and independently checkable commitments. Its weakness is not missing another blockchain feature; it is that the provenance of a source and the authority of its issuer are easily confused. The best competitive response is to make that distinction visible and demonstrate what happens when trust is insufficient.

## 2. The strongest product proposition

**Share the fact, not the file—and show exactly what has been verified.**

Use a concrete student workflow: a recipient needs one academic attribute, while a marksheet reveals identifiers, date of birth, every subject and other unnecessary details. Foliolet lets the holder inspect extraction evidence, confirm a chosen fact, anchor a salted commitment and disclose only the selected claim with a portable proof. It makes a changed proof fail and makes missing issuer authority explicit.

This is a useful integration proposition, not a claim that selective disclosure or document wallets are newly invented. Its strongest demonstrated distinction is the continuous path from a messy holder-supplied legacy document, through inspectable source review, to restricted disclosure and independent lifecycle-aware verification. Its commercial value remains a hypothesis until a verifier agrees to rely on its assurance model. No user study, paying customer or institutional deployment was established in this run.

A signed, standardized credential issued directly by a trusted university is preferable when available. Foliolet should be a bridge for mixed legacy documents and a privacy-aware presentation workflow, not an alternative authority that declares untrusted PDFs genuine.

## 3. Comparison with established approaches

| Approach / primary source | Established strength | Foliolet's defensible role and limitation |
|---|---|---|
| [DigiLocker issued documents](https://wb.digilocker.gov.in/web/about/faq) and [NAD academic credentials](https://nad.digilocker.gov.in/faq) | Issuer-connected records and an established Indian ecosystem; uploaded files and issued records are different categories | Local assisted intake avoids requiring organizational API approval, but does not inherit issuer authority merely by reading a downloaded PDF |
| [W3C Verifiable Credentials Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/) | A standardized issuer/holder/verifier data model and explicit trust relationships | Current Foliolet JSON/Merkle presentations are not automatically W3C-VC interoperable; importing/exporting standards is future work |
| [RFC 9901 SD-JWT](https://www.rfc-editor.org/rfc/rfc9901.html) | Standardized selective disclosure using salted disclosures and issuer-signed structures | Merkle selection is a different existing construction, not a novel replacement for SD-JWT; an adapter requires real issuer semantics and compatibility tests |
| [OpenID for Verifiable Presentations 1.0](https://openid.net/specs/openid-4-verifiable-presentations-1_0-final.html) | Standardized presentation requests and wallet/verifier exchange | Current bearer-link/QR flow does not implement this protocol or authenticate a recipient merely from an audience label |
| [Blockcerts](https://www.blockcerts.org/guide/) | Established blockchain-backed credential verification concepts | Foliolet cannot claim to invent blockchain credential integrity; its current emphasis is holder-selected legacy facts and source review |
| [walt.id](https://docs.walt.id/) | Existing credential, wallet and identity tooling | A credible production direction is integration with mature standards tooling, not rebuilding the whole ecosystem during the finale |
| Plain PDF/email | Ubiquitous, immediately readable, low setup burden | Reveals the whole source and offers little disclosure minimization; however it may carry a genuine issuer signature that must not be discarded or overstated |

The W3C standard explicitly separates verification mechanisms from an application's trust decisions. The standards above are mature prior art. Their existence strengthens the need for accurate novelty claims and offers future interoperability paths; it does not invalidate Foliolet's narrower workflow demonstration.

## 4. Practical issuer and source-assurance options

| Method | Individual accessibility | What can actually be established | Decision |
|---|---|---|---|
| Local detached PDF signature inspection | No government approval or paid API needed for supported files | Digest/signature mathematics and current-file coverage; embedded certificate fingerprint | Implemented with pyHanko and no implicit trusted roots; always distinguish untrusted issuer |
| Independently provisioned issuer roots and authority policy | Public certificates may be accessible | A certificate path plus an explicit mapping from signer authority to credential type; relevant revocation/time evidence still required | Defer issuer badge until policy and real corpus exist |
| QR extraction | Local decoding is accessible | Presence/content of a QR, not authenticity | Retain indicator only; never auto-fetch arbitrary URLs or treat a logo/QR as issuance |
| Supported signed XML/JSON credentials | Feasible for a specified format with known keys | Integrity and signer control under the chosen key/authority policy | Valuable later, but no universal importer added without fixtures and trust policy |
| Public issuer verification website | Sometimes lawful individual access exists | Whatever that issuer actually confirms for that record | No scraping, CAPTCHA bypass or private identifier transmission was made a dependency |
| Holder e-signature or new key pair | Individually feasible | Consent/control of that holder key | Does not turn a holder-created document into a university-issued credential |
| Institutional DigiLocker/API partnership | Requires approvals outside this assignment | Potentially strong issuer-linked acquisition | Not a prerequisite for the finale |
| Self-declared threshold statement | Easy to commit | Inclusion of a statement the platform/holder asserted | Not a zero-knowledge proof of a hidden grade comparison |

India's [CCA signature verification guidance](https://www.cca.gov.in/index.php/signature_verification.html) and [root certificate publication](https://www.cca.gov.in/root_certificate.html) distinguish the necessary certificate and validation context. Simply downloading a public root or trusting the certificate embedded in the PDF is not an issuer-authority policy. Offline verification without fresh revocation evidence must state that limitation.

[pyHanko validation documentation](https://docs.pyhanko.eu/en/stable/lib-guide/validation.html) provides a practical implementation route. The implemented feature deliberately stops at supported signature inspection. It does not add `ISSUER_VERIFIED`, weaken the on-chain assurance enum or silently promote a self-signed certificate. A valid self-signature and a tampered signed PDF are both tested; they produce different mathematical results while issuer authority remains unestablished.

## 5. Document datasets: suitability, licensing and actual use

| Dataset / source | Suitable evaluation task | Licensing/access and decision |
|---|---|---|
| [CORD original project](https://github.com/clovaai/cord), [CORD v2 distribution](https://huggingface.co/datasets/naver-clova-ix/cord-v2) | Real receipt OCR and semantic association, including totals and confusing nearby identifiers | Explicit CC BY 4.0. Eight fixed public samples acquired, original human labels retained, attribution and hashes recorded. Two calibration / six held out |
| [DocLayNet](https://github.com/DS4SD/DocLayNet) | Layout regions across diverse documents | CDLA-Permissive-1.0; useful for layout, not directly a marksheet key/value ground truth. Full large corpus not downloaded merely to inflate dataset count |
| [FUNSD](https://guillaumejaume.github.io/FUNSD/) | Noisy forms, question/answer/entity relationships | Official overview describes 199 annotated forms. Dataset redistribution rights were not established from the fetched overview; no source bytes ingested or republished in this run |
| [SROIE organizer portal](https://rrc.cvc.uab.es/?ch=13) | Receipt text and information extraction | Official portal timed out in this run. Applicable current access/redistribution terms were not verified; not ingested |
| Genuine Indian academic documents | The target product's real generalization test | No sufficiently diverse consented, independently labelled and legally redistributable corpus was established. This remains a gap, not a synthetic substitute labelled “real” |
| Fictional/adversarial PDFs | Known exact facts, deliberate contradictions, rotations, hidden text and OCR confusion | Fourteen generated documents, 169 labelled facts, explicit fixture category; not issuer-authenticated or representative population data |

CORD's public release is smaller than the complete collection described by its authors. Its official project also notes removals of some sensitive annotation classes. Public availability is not a reason to display receipt identifiers unnecessarily. This report publishes only the narrow evaluation outcomes and provenance metadata; no private user document is included.

The paired synthetic result remained 99.41% recall / 98.82% precision including review suggestions. The held-out receipt totals exposed a wrong association and unsupported currency normalization. Dataset human annotations, not the model's own guesses, supplied the total targets. Exact source spans and review flags are reported separately from correctness. See [EVIDENCE.md](EVIDENCE.md) for the denominator, per-case outcomes, failure history and resource definitions.

## 6. OCR and local-model decisions

The working native-PDF + Tesseract + complementary local OCR pipeline was retained because the assignment required measured alternatives, not a fashionable replacement. The audit measured its real behavior, fixed association/assurance errors and preserved deterministic validation. It did not benchmark a complete PaddleOCR/Docling/vision-model replacement under comparable conditions, so it does not claim that the selected pipeline is globally superior.

Actual local Qwen3 4B inference was executed after model download inside an OS network namespace with only loopback. The 10-case strict answer/citation rubric passed five cases; the separate actual Foli/Spring-AI transport passed three focused cases. No tool-driven write capability was granted. These results favor an optional, read-only assistant with visible sources and abstention—not model authority over verified facts. See the final acceptance report for exact model digest, timings and limitations.

## 7. Hosted providers: verified access is not permission to upload

[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing.md), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) and [terms](https://ai.google.dev/gemini-api/terms.md) distinguish available unpaid usage from how submitted content may be handled. Unpaid-service terms include data-use/review conditions and cautions about sensitive information, with jurisdictional exceptions. No private source was uploaded and no account-specific quota was assumed.

[Groq data handling](https://console.groq.com/docs/your-data) and [rate-limit documentation](https://console.groq.com/docs/rate-limits) require attention to endpoint/account behavior, exceptions and settings; blanket “nothing is retained” claims are not justified. No API key or configured zero-data-retention account was available or assumed for this assignment.

[NVIDIA hosted API access](https://docs.api.nvidia.com/nim/re/docs/api-quickstart) and [developer terms](https://developer.nvidia.com/legal/terms) do not establish a universal perpetual free quota for this user's account. Old promotional-credit numbers were not treated as current entitlement. No paid or organizational approval dependency was introduced.

**Decision:** sensitive document processing remains local by default. Hosted providers are optional future experiments only after explicit authorization, current account/quota verification and privacy review. Their existence is not evidence that they would improve Foliolet's measured accuracy.

## 8. Rejected finale directions

Do not add an NFT merely to label ownership, a ZK badge without a circuit, a government-verification badge from a QR, a cloud model that receives documents silently, or an untested new wallet standard that breaks existing proofs. Do not describe a single-operator Ganache chain as decentralized production infrastructure. Do not replace real adversarial demonstrations with a larger feature list.

The recommended finale improvement is already concrete: show three distinct questions—does the source say this, was this committed fact changed, and is the issuer actually trusted? Foliolet now provides inspectable evidence for the first two and a truthful boundary for the third. That makes the demonstration technically credible even under skeptical questioning.
