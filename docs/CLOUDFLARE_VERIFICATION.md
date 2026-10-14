# Receiver tunnel verification, 14 October 2026

The implementation and verification are local to branch `testcloudflare` in
`C:/Users/User/Downloads/Foliolet-testcloudflare`. Its exact starting commit is
Foliolet `origin/main` **b810d2a07a1e2aec9a9fc4d8a8c2d1aaaec2b5f2**, fetched from
`https://github.com/legoambarish/Foliolet.git`. The local `main` ref remains the
legacy upstream commit **c04741ee68563566dc82ab4e71b97c3898714f72**; it was never
checked out, committed to, merged or pushed. No remote push or PR was made.

The previous checkout `C:/Users/User/Downloads/Evidentia` remains on
`codex/foliolet-evidence-bridge` at
**bcf7e724396c0d28341d7a4a4b7b09da1af1fae1**, as does `testbuilds`. Its tracked
diff is still empty and its original untracked `docs/EVOLUTION_FROM_EVIDENTIA.md`
and `output/` remain present. No previous redesign source or retained database,
chain, vault, session or signing key was imported. The existing portable
PostgreSQL executable directory was reused read-only; this worktree has its own
new PostgreSQL data directory and all other runtime state.

See [the plan](CLOUDFLARE_PLAN.md) for the source inspection and decisions made
before implementation, and [the run guide](CLOUDFLARE_RECEIVER.md) for exact
Windows/POSIX startup, configuration, stop/restart, security boundaries and the
repeatable phone demo.

## Automated suites

Commands below run from this worktree unless an explicit directory is shown.
Counts describe each suite separately; reruns are not additional tests.

| Suite | Command | Actual result |
| --- | --- | --- |
| Original Django baseline | In `django-service`: `..\.venv\Scripts\python.exe manage.py test dashboard` | 27 passed before edits |
| Final Django, including boundary/lifecycle/publication failures | Same command | **50 passed**, 27 existing plus 23 new |
| Private Django settings | In `django-service`: `..\.venv\Scripts\python.exe manage.py check` | No issues |
| Receiver deployment settings | In `django-service`: `..\.venv\Scripts\python.exe manage.py check --settings=hermes.receiver_settings --deploy` | Exit 0, intentional HSTS warnings W005/W021; no errors |
| Spring original package/tests | In `spring-boot-service`: `mvnw.cmd -B package` | **25 passed**, package built; no Java changes |
| Original browser/cryptographic verifier | `npm run test:verifier` | **22 passed** after the final JS change |
| Share URL/copy/QR input equivalence | `node --test tools/test-share-qr.cjs` | **1 passed**, exercising real `wallet.js` with copy/encoder spies |
| Original Solidity/Ganache checks | `npm run test:contracts` | Passed authorization, immutable commitment, assurance, supersession, revocation and seven Merkle-shape assertions; script has no numbered test-runner total |
| Existing live holder workflow | `.\.venv\Scripts\python.exe tools/test-live-workflow.py` | **51 checks passed** with real isolated PostgreSQL/Spring/EVM/Django |
| Existing live security workflow | `.\.venv\Scripts\python.exe tools/test-live-security.py` | **23 checks passed** |
| Actual public HTTPS receiver | `.\.venv\Scripts\python.exe tools/test-public-sharing.py` | **40 checks passed** on final receiver settings |

The live workflows create only their own synthetic accounts/documents. Expiry
testing moves only its own synthetic grant's expiry into the past in the isolated
database; it does not claim that a real 30-minute timer was observed. First live
workflow startup failed because the fresh virtual environment lacked `watchdog`;
installing the repository's existing `tools/requirements-dev.txt` resolved that
dependency and the full 51-check rerun passed. Node 25 uses Ganache's JavaScript
fallback because its optional native uWS module is unavailable; the real chain
and contract checks still passed.

## Actual public HTTPS evidence

The final 40-check run passed from **18:27:59 to 18:29:01 IST (+05:30),
14 October 2026**. It used the actual Cloudflare edge, not localhost or a mocked
tunnel. The HTTPS client and the subsequent in-app browser were on the holder's
computer/network. A separate physical device/mobile-data network was unavailable
and is **NOT TESTED**.

Observed hostname before deliberately killing the connector:
`employment-priority-katrina-efficiently.trycloudflare.com`.
The recovered, verified hostname:
`endif-going-poker-reveals.trycloudflare.com`.
These are historical test observations, not configuration or permanent URLs.
Bearer tokens are omitted. Hostnames alone do not grant access to facts.

| Operation on the public HTTPS origin | Observed HTTP/result |
| --- | --- |
| Recipient GET, then HEAD | 200; landing only, no facts; grant views remained zero |
| Explicit CSRF-protected release | 200; exactly the authorized threshold, no exact CGPA/name/institution/DOB |
| Two simultaneous POSTs on a one-time grant | Exactly one successful release; the other receives the existing denial page |
| Second one-time POST | 200 denial page, no facts; existing Spring policy denies the release |
| `/`, `/admin/`, `/login/`, `/register/`, `/wallet/`, `/sharing/`, `/integrity/`, `/api/`, `/api/public/network`, `/legacy/`, `/.local-data/`, `/status`, `/static/admin/js/core.js` | All 404 |
| Referenced landing CSS/JS/font resources | All 200 |
| Forged Origin with valid form CSRF token | 403 before release |
| Forged Host | 530 at Cloudflare edge; direct receiver boundary tests return 400 |
| Correct browser-session proof export | 200 JSON; only the released threshold/proof |
| Different browser-session export | 404 |
| Revoked and expired grant POSTs | 200 denial pages, no facts; original UI intentionally renders policy denial as HTML 200 |
| Two simultaneous holder share creations | Both reused the same active hostname and connector PID |
| Owned connector terminated | Status changed to unavailable, active origin omitted |
| Next holder share | Automatically replaced the dead connector, validated a new public hostname, then released facts successfully |

The final browser demonstration at **18:30 IST** used the same recovered origin:
select one threshold/five withheld, create a repeatable 30-minute share, render
the actual 261-pixel QR, confirm preview equals the receipt field, press Copy
(UI reported “Copied”), open the actual HTTPS landing, then explicitly release
the threshold. The browser's observed asset inventory contained eight resources
(three scripts, four fonts, one stylesheet), all from the public origin, and
zero localhost/127.0.0.1 resources. This inventory is not a packet capture.
The public verifier has no independent-check button, RPC input, ethers script or
chain-request branch; it explains that no independent browser chain check ran.

The in-app browser clipboard readback API returned empty text despite the Copy
button's success message. Therefore actual clipboard readback is **NOT VERIFIED**;
the real JS input equivalence test passed. The browser's actual QR image also
matched byte-for-byte the local QR generator's encoding of the exact receipt URL
(same size/error correction), and the preview matched. This is a rendering/encoding
comparison, not an independent decoder or physical scan; neither was performed.
No successful mobile scan is claimed.

## Failures retained and downtime behavior

Initial real Quick Tunnel experiments included bounded readiness timeouts with
a registered connector but unavailable local DNS/public routing. The default
startup limit was changed from 40 to 60 seconds, the first health probe waits
three seconds after URL discovery, and the connector uses supported HTTP/2.
These changes did not justify claiming that the environment's DNS was repaired.

The first final rerun failed safely at approximately **18:25 IST** on
`structural-sample-processor-collectables.trycloudflare.com`: Windows
`socket.getaddrinfo` returned `gaierror 11001`, while explicit Cloudflare DNS over
HTTPS and Google DNS returned valid public addresses. The app did not publish a
share receipt. No DNS configuration, hosts file or global cache flush was
performed. The fresh-hostname retry completed all 40 checks without manual DNS
priming for its two hostnames. The integration deliberately requires actual
public HTTPS health rather than bypassing a failed resolver or trusting a
printed URL. A recurring resolver/connectivity failure needs an operator network
fix; the holder receives a bounded error and can retry.

Unit regressions additionally cover missing executable/start failure, timeout
cleanup of the owned child, rejection of another receiver's health instance,
live connector outage without silent hostname rotation, stale hostname during
publication, cross-process lock exclusion, simultaneous ensures, invalid returned
links, malformed creation responses, ambiguous backend creation failure and
revocation failure after an unpublished grant is created. A stalled real network
was observed as the DNS readiness timeout; arbitrary cable/firewall failure modes
were not separately injected.

An explicit stop was exercised: the owned connector/supervisor exited and ports
8001/8002 closed. Subsequent sharing created a new managed receiver/tunnel.
No global process-name termination, deletion of other tunnel configuration, or
kill based on a stale PID file is used by the feature.
The private development log filter was also exercised against the final restarted
Django process: an ordinary login GET was logged, while a valid-format verify GET
was omitted; both returned HTTP 200. No bearer paths remained in its retained log.

## Acceptance matrix

| # | Required acceptance | Result and evidence boundary |
| --- | --- | --- |
| 1 | Inspected main, isolated branch, preserved old work | PASS; exact base/ref/status checks above |
| 2 | First share starts ready receiver/tunnel or errors before granting | PASS; actual cold creation and startup/publication failure tests |
| 3 | Correct public HTTPS `/verify/<token>/` URL | PASS; live receipt and strict URL/path tests |
| 4 | Copy and QR encode identical URL | PASS for real JS input equivalence, actual QR image equivalence and preview; clipboard readback and physical scan NOT VERIFIED |
| 5 | Second device on mobile data GET | **NOT TESTED**; no second physical device/network available; actual public HTTPS GET on holder computer passed |
| 6 | Explicit recipient POST, selected facts only | PASS on real HTTPS and browser; physical mobile POST NOT TESTED |
| 7 | Repeat/simultaneous one-time opens | PASS, real concurrent HTTPS POSTs |
| 8 | Expiry/revocation | PASS, synthetic expiry fixture and real owner revocation |
| 9 | Private routes denied publicly | PASS, 13 real public negative routes plus unit allowlist checks |
| 10 | Assets/sessions/CSRF/cookies/debug/proxy | PASS, real HTTPS and final receiver deployment checks with documented HSTS warnings |
| 11 | Second/simultaneous shares reuse tunnel | PASS, same connector PID and active origin |
| 12 | Dead/unavailable tunnel fails accurately | PASS, real connector death, real DNS timeout, deterministic timeout/start/outage tests |
| 13 | Restart uses only newly verified host | PASS, recovery and orderly stop; temporary-link warning visible |
| 14 | No hidden localhost/public RPC dependencies | PASS for browser-observed assets, public HTML/JS/CSP and private listener/route checks; packet capture not performed |
| 15 | Existing holder workflow/tests | PASS, suites above; no Spring/contracts/grant-semantic changes |
| 16 | Scoped diff, no secrets/main changes/push | PASS, final scoped staging/diff/status review; all keys, binaries, logs, fixtures and screenshots ignored |

## Remaining operator checks and retained demo

- Scan a newly generated QR with a real second phone, Wi-Fi disabled and mobile
  data enabled; perform the full checklist in the run guide. This is the remaining
  cross-network acceptance step, not a reason to deploy a private route.
- Named mode requires an already provisioned user-owned Cloudflare zone/connector;
  no credentials/domain were available, so live named mode is NOT TESTED.
- POSIX runtime/teardown is NOT TESTED on this Windows machine.
- A one-hour HSTS header is enabled only for the active receiver hostname; the
  intentional W005/W021 warnings retain no includeSubDomains/preload policy.
  The profile intentionally has no mail backend and silences only mail.W001.
- Bearer links can be forwarded; intended-for is not authentication. Revocation
  cannot erase received data. Cloudflare terminates TLS and can see bearer paths
  and disclosed contents. Public independent browser EVM verification remains
  unavailable; service checks and session-bound proof export were exercised.

At handoff the isolated synthetic demo stack is running: loopback PostgreSQL
55432, EVM 8545, Spring 8080, private Django 8000, receiver 8001 and authenticated
local control 8002. One managed Quick Tunnel is active. Runtime captures/results
live only in ignored `.local-data/` (`cloudflare-public-results.json`,
`cloudflare-public-retry.log`, retained failed `cloudflare-public-final.log`,
`cloudflare-browser-assets.json`, `cloudflare-browser-qr-check.json`, `cloudflare-receipt-final.jpg`,
`cloudflare-receiver-final.jpg`). Synthetic fixture credentials remain only in
ignored `.local-data/cloudflare-demo.json`. The browser demo share expires at
19:00 IST; restarting/stopping its Quick Tunnel invalidates its URL/QR earlier.
Use `.\.venv\Scripts\python.exe tools/share-tunnel.py stop` to close only this
receiver/tunnel. Full original-service shutdown remains as documented in
[RUN_GUIDE.md](RUN_GUIDE.md).
