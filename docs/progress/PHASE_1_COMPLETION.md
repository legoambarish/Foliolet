# Phase 1: implemented and locally verified

Governed contract, issuer/type scopes, immutable typed evidence, suspension/reinstatement, atomic supersession and irreversible revocation are implemented. Holder keys are generated/imported in the browser, and sign exact EIP-712 presentations against signed verifier requests. Decisions and consents retain bounded context, read blocks and audit records. The independent reader takes separate trust pins and reads RPC directly.

Actual tests cover role/owner refusal, wrong holder, audience/nonce/policy tampering, Merkle leaf/salt/path changes, typed semantics, stale/missing pins, lifecycle transitions, one-opening release, nonce idempotency and historical reproduction. Browser role flows and mobile rendering were exercised. Recovery simulates a committed chain record whose database lifecycle remains pending, then reconciles it without changing commitments. It is not a real process-crash test.

Counts and artifact hashes are derived in `../verification-results.json`. The offline rehearsal stops AI, Spring and private Django; independent historical/current checks pass while RPC remains available, and current status becomes UNKNOWN without RPC. Imported source truth, test institutional recognition, downloadable-copy control and production signer custody remain explicit limits.
