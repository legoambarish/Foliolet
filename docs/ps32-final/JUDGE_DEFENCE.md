# Grand-finale strategy and skeptical judge defence

## Presentation spine

Lead with over-disclosure, not technology names. Show a fictional marksheet and identify the single fact the recipient needs. Walk through source review, minimal disclosure, independent verification and a deliberate failure. Only then explain the architecture. The most memorable technical moment is a valid self-signature that is still honestly marked as an untrusted issuer, followed by a changed original that fails its digest check.

Use five conceptual slides: the privacy problem; the actual workflow; the separate assurance dimensions; measured evidence and negative cases; the adoption path. Show real functionality between slides. Do not fill slides with every library or future feature. Keep an evidence appendix with exact source revision, test runs, benchmark denominators and deployment limitations.

The defensible novelty statement is: **“We integrate source-reviewed legacy-document intake with minimal disclosure and independently checkable, lifecycle-aware proofs, while making missing issuer authority explicit.”** Do not say that Merkle trees, digital signatures, blockchain credentials or NFC are inventions of this project.

## Judge-question bank

### 1. Why should anyone use this instead of sending a PDF?
A PDF often reveals much more than the recipient needs. Foliolet reveals selected committed fields and their proofs, not the original or all hidden fields. The benefit is disclosure minimization and an inspectable workflow. Where a trusted issuer already supplies a standards-compatible selective-disclosure credential, that may be the better source.

### 2. Why not use DigiLocker alone?
DigiLocker is valuable for issuer-connected documents. Our local assisted intake is not an equivalent issuer API. Foliolet focuses on what a holder discloses from mixed legacy documents and how the recipient checks that presentation. Downloading a file from a branded source does not automatically give our platform issuer-verification authority.

### 3. Can I upload a fake marksheet and get a valid proof?
Yes, a false source can produce a valid integrity commitment. The proof establishes what was committed, not whether the institution issued it. That limitation is explicit. We added local signature inspection, but a self-signed file still does not become institution-verified.

### 4. What is genuinely new?
Not the cryptographic primitives. The product hypothesis is the source-to-disclosure workflow, inspectable extraction, modification tracking, explicit assurance separation and portable verification for legacy documents. We have not established that no competitor offers a similar combination. We defend usefulness and working evidence rather than an unsupported first-ever claim.

### 5. Why is blockchain necessary?
It provides an independently queryable commitment/status registry in this design. A transparency log or other independently verifiable registry could serve similar purposes. We do not claim blockchain is mathematically necessary for privacy. Its value here is demonstrating an external verification boundary, not adding a token.

### 6. Is this decentralized?
The demonstration uses a single-operator local Ganache deployment and custodial signing. It is not decentralized production consensus. Separate verifier code can check the recorded state under pinned identities, but the operator and infrastructure remain trust assumptions.

### 7. What does a Merkle proof prove?
That a canonical selected leaf belongs to the committed root under the specified encoding and hash assumptions. It does not prove the underlying claim is true, identify its issuer or show a hidden arithmetic predicate. Random salts reduce simple guessing of undisclosed small-domain values.

### 8. Do you put documents or all marks on-chain?
No. The tested wallet anchors commitments and lifecycle state. Selected claims and proof material are disclosed to recipients; the encrypted original remains private. Transaction timing, roots, operator identity and repeated presentations can still support correlation, so “zero metadata leakage” would be false.

### 9. Does the holder sign the presentation?
The current presentation is signed by the platform's custodial key. Holder review and authenticated actions record consent in the application, not a holder-controlled cryptographic signature. Noncustodial consent keys are a future migration, not a current guarantee.

### 10. How is verification independent?
Separate JavaScript/Node logic recomputes canonical leaves, Merkle roots and signatures, and queries the EVM using separately provisioned contract/operator/network pins. Pins must not be accepted from the untrusted proof itself. Independence of code does not eliminate trust in the selected chain and its operator.

### 11. What happens if someone changes a value, label or type?
The live attack suite mutates proof components and expects rejection. The commitment encoding binds typed claims and metadata rather than accepting a convenient interpretation of arbitrary JSON. Genuine positive controls remain valid, so a verifier that rejects everything would not pass the suite.

### 12. Does a DigiLocker logo or QR code prove authenticity?
No. A logo is an image and an arbitrary QR is encoded data. We can detect indicators, but issuer verification requires a supported cryptographic or issuer-authoritative process. We do not follow an arbitrary QR URL and declare its content trusted.

### 13. What does the new PDF signature feature actually verify?
For supported detached PDF signatures, it inspects the signed-byte digest, signature mathematics and whether the signature covers the entire current file. It binds the report to the original SHA-256. No trusted issuer roots/authority policy or fresh revocation evidence are provisioned, so issuer authenticity remains unestablished.

### 14. Why can a self-signed PDF pass the signature check?
Anyone can create a key and correctly sign bytes. That proves a mathematical relationship, not the signer's institutional authority. The UI deliberately separates those questions. The demonstration shows valid mathematics with an untrusted issuer rather than manufacturing a government badge.

### 15. Does offline verification establish current revocation status?
No. Mathematical checks can be performed offline with trusted local material, but freshness requires applicable status evidence. The signature inspector does not invent revocation information. A downloaded proof may remain mathematically valid after its grant is revoked; online policy evaluation must reject it when freshness is required.

### 16. Can revocation retract data already seen?
No. It blocks future authorized release/verification under the policy; it cannot erase a copied value, screenshot or exported proof. The product should minimize what is disclosed in the first place, not promise impossible recall of knowledge.

### 17. Can two recipients race a one-time link?
The actual PostgreSQL-backed concurrency test exercises simultaneous release and establishes one successful opening in that scenario. Release is a POST operation protected by transactional locking; preview GET does not consume the grant. That does not prove correctness under every possible distributed production topology without further load/fault testing.

### 18. Can a link be forwarded or opened by a scanner?
A bearer link can be forwarded. An audience label is not recipient authentication. GET preview/link scanning is separated from consuming POST release, but a client that actively submits the consuming action can still spend a bearer capability. Authenticated-recipient grants are future work when that guarantee is required.

### 19. Does NFC add security?
It can make the same disclosure URL convenient to open. It does not stop copying, establish issuer identity or authenticate a recipient. Physical NFC/mobile behavior was not tested in this run; software QR tests are not a substitute for a real device rehearsal.

### 20. What if OCR reads 9O as 90?
That exact class of error remains in the adversarial corpus. It is review-required, not automatically accepted, and the original remains inspectable. A review flag prevents silent acceptance but does not make the suggestion correct. Source alignment and OCR confidence are not certainty.

### 21. Your synthetic score is 99.41%; is that real-world accuracy?
No. It is recall including review suggestions on 169 labelled facts in 14 fictional PDFs. Precision was 98.82%, with zero false automatic suggestions and two false review suggestions. Eight genuine public receipts exposed weaker out-of-domain association. We report both rather than presenting synthetic performance as universal accuracy.

### 22. What did the held-out real documents show?
On six preselected held-out receipt totals, four were correct normalized decimals; a fifth identified the right source literal but lacked currency normalization, and one selected an unrelated identifier. All outputs required review. These small, narrow fractions do not establish accuracy on Indian academic documents.

### 23. Did an LLM generate your ground truth?
No. Fictional documents have explicit known labels, and public CORD samples retain the dataset's human annotations. The narrow receipt-total comparison was checked against those annotations and the source images. The model's own answer is not accepted as ground truth.

### 24. Can prompt injection change a grade or anchor a document?
The model has no authorized write/anchor tools. Its output is untrusted, source-bound and subject to deterministic application checks and holder review. One tested injection canary was suppressed, but we do not claim general prompt-injection immunity. The strict real-model answer/citation rubric passed only five of ten cases.

### 25. Why keep AI if it sometimes cites incorrectly?
As optional reading assistance, not verification authority. The source and uncertainty are visible, and core disclosure/cryptographic verification does not depend on a model being online. Incorrect or excessive evidence references are retained as negative test outcomes. More model output is not automatically a better product.

### 26. What happens when the model, OCR, database or chain is down?
Missing OCR/model cases preserve originals and expose limitations. Actual database and EVM interruption tests fail closed rather than returning a stale green result. The same database/chain/key state is restarted and previously valid proofs remain valid after recovery. The final evidence gives the observed failure and restart timings.

### 27. How are originals and login sessions protected?
Wallet originals use authenticated encryption with preserved local keys. New server-side sessions are encrypted JSON inside Django's signed envelope. We added owner-only POSIX permissions, bounded reads and path/symlink checks. A compromised host or attacker who obtains both data and keys is not excluded by these protections.

### 28. Can private documents leak to a hosted model?
The legacy cloud-analysis route was a real privacy risk: an empty API key still allowed sending a request body. It now defaults to denial before source reads/network and requires explicit administrator and request consent plus a key. No cloud mode was enabled and no private document was uploaded during this assignment.

### 29. Did you find every vulnerability?
No. We inspected relevant first-party modules, ran static/dependency tools, reproduced targeted failures and exercised real adversarial workflows. A coverage register distinguishes inspected, executed and uncertain areas. Ganache/deployment risks, broader malicious-PDF resource attacks and production hardening remain explicit.

### 30. Are you production-ready?
Not for arbitrary public documents or institutional reliance without further controls. The tested local workflow is a credible controlled demonstration. Production requires a supported chain runtime, hardened deployment and secrets, global resource/rate limits, formal issuer policy, real academic corpus validation and broader fault/load/backup testing.

### 31. What is the commercial path?
Validate a narrowly defined verifier workflow first, such as minimizing data exchanged for a student or professional eligibility check. Measure reduced unnecessary disclosure, review effort, support burden and verifier acceptance. We have not established paying customers, savings or market share; those are hypotheses, not achievements.

### 32. Does your existing code comply with hackathon rules?
We must disclose pre-existing work accurately. The organizer's exact prebuilt-code eligibility rule was not independently established in this run. We can show the baseline, isolated implementation history and work performed here, but cannot infer eligibility from technical merit or conceal the project's history.

### 33. What is your strongest evidence against an excellent competing team?
A real source-to-proof workflow, a baseline defect that was reproduced before repair, independently executed verifier attacks, actual one-time concurrency, preserved-state outages/restarts and candid real-document/model failures. Those demonstrate engineering understanding. They do not guarantee a win; judging and competing solutions remain outside our control.

## Questions that could decide the result

The three dangerous questions are “Can a fake document still pass?”, “Why not DigiLocker/VCs?” and “What is actually novel?” Answer directly before explaining the architecture. Do not dodge with encryption, NFTs or AI. Show the assurance boundary, the privacy benefit and the working evidence. A candid limitation supported by a deliberately rejected case is more persuasive than an unsupported green badge.
