# Public selective disclosure with Cloudflare Tunnel

This branch starts from original Foliolet main, not Evidence Bridge. It changes
only how an existing disclosure reaches its receiver. Spring's grant/token,
encryption, selected facts, expiry, atomic one-time release, source status and
revocation remain the authority. Nothing here certifies issuer authenticity.

[Verification and the 16-item acceptance matrix](CLOUDFLARE_VERIFICATION.md)
record actual tests, public HTTP evidence, retained failures and remaining device
checks for this branch.

## Start on Windows PowerShell

Work in `C:\Users\User\Downloads\Foliolet-testcloudflare`, branch `testcloudflare`.
Install/start the original isolated core using [RUN_GUIDE.md](RUN_GUIDE.md):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r django-service/requirements.txt -r tools/requirements-dev.txt
npm ci
npm --prefix spring-boot-service ci
.\tools\install-cloudflared.ps1
.\tools\setup-local-postgres.ps1
.\tools\start-postgres.ps1
# Keep each of the following running in its own terminal:
npm run evm
.\tools\start-backend.ps1
.\tools\start-frontend.ps1
```

Open [the private application](http://localhost:8000/). Enroll only a synthetic
document for an initial tunnel demo, confirm its facts, anchor the commitment,
then **Share a proof**. Select the required facts and create a link. The first
public share automatically starts the receiver and a Quick Tunnel; allow up to
about a minute for startup. The receipt, preview, clipboard and QR use the same
verified HTTPS URL. A failure shows an error before creating a grant. No Cloudflare
login, domain, payment, DNS mutation or raw backend publishing is needed.

The Windows installer downloads the official x64 release into ignored
`.local-tools/cloudflared/cloudflared.exe`, validates SHA-256 against the GitHub
release asset digest and preserves an existing local binary. Tested release:
2026.10.0, SHA-256 `86aee4017b26625cee8484c113558f48effa4cd47f7aa05fcf425604e5d2b23c`.
You can instead install from [Cloudflare downloads](https://developers.cloudflare.com/tunnel/downloads/)
or set `CLOUDFLARED_PATH` to an already installed executable. No binary is committed.

## Local controls and modes

Run these in the same checkout with the same configuration as private Django:

```powershell
.\.venv\Scripts\python.exe tools/share-tunnel.py status
.\.venv\Scripts\python.exe tools/share-tunnel.py start
.\.venv\Scripts\python.exe tools/share-tunnel.py stop
.\.venv\Scripts\python.exe tools/share-tunnel.py restart
```

`start` is idempotent and reuses a healthy tunnel. `status` verifies public health
when ready; error output/exit code reports failed health. A hostname in
`lastOrigin` is diagnostic history and is **not** an active share origin.
`stop` terminates only this authenticated supervisor's receiver/cloudflared.
`restart` changes Quick Tunnel hostnames and invalidates already sent links/QRs.
Explicitly stop before shutting down the application. Stopping just private Django
does not stop the detached receiver: this preserves links across private UI reloads.
Stopping Spring/EVM prevents facts from being released or freshly exported.

Environment settings must be set explicitly in the private Django/control
terminal. `.env.example` documents them; PowerShell does not source `.env`.

| Setting | Default and purpose |
| --- | --- |
| `FOLIOLET_SHARE_MODE` | `quick`; alternatives `local`, `named` |
| `CLOUDFLARED_PATH` | PATH, then this checkout's `.local-tools/cloudflared` |
| `FOLIOLET_RECEIVER_PORT` | `8001`, loopback only; must differ from private/core ports |
| `FOLIOLET_CONTROL_PORT` | `8002`, secret-protected loopback control; never publicly routed |
| `FOLIOLET_TUNNEL_TIMEOUT` | `60` seconds; configurable 10–60, bounded startup |
| `FOLIOLET_PUBLIC_BASE_URL` | Required only for named mode; exact HTTPS origin, no path/port/query |
| `WALLET_SHARE_BASE_URL` | Original Spring startup setting; normally `http://localhost:8000` |
| `SPRING_BOOT_API_BASE_URL` | Original private server-side bridge; `http://localhost:8080` |

Stop the supervisor and restart private Django when changing sharing configuration.
Public Django does not inherit the private app's allowed hosts, debug mode, cookie
names, secret or sessions. Its backend environment is inherited at supervisor
startup. A missing executable/connectivity problem never causes silent local fallback.

For deliberate local-only development:

```powershell
$env:FOLIOLET_SHARE_MODE = 'local'
.\tools\start-frontend.ps1
```

No receiver/tunnel is started, and the receipt warns that the local link/QR only
works on the holder computer. Spring's local share base should stay consistent.

### Already provisioned named tunnel

No named tunnel credentials/domain were available in this run, so live named mode
is **not tested**. The integration supports an operator-managed, already provisioned
tunnel without creating/managing account resources. Point only its public hostname
at `http://127.0.0.1:8001`, leave the incoming Host intact and have cloudflared set
the HTTPS forwarded scheme. A local ingress configuration must end in
`service: http_status:404`; remotely managed ingress should route only this receiver.
Never point it at ports 8000, 8080 or 8545. Keep its token/config outside Git.

```powershell
$env:FOLIOLET_SHARE_MODE = 'named'
$env:FOLIOLET_PUBLIC_BASE_URL = 'https://proofs.your-own-domain.example'
.\tools\start-frontend.ps1
```

The app starts the receiver and proves that this hostname reaches its exact random
health instance before publishing grants. It does not launch, stop or administer
the operator's named connector. A stable hostname still needs running services.
If setting `WALLET_SHARE_BASE_URL` in Spring to the same stable origin, set it in
the Django terminal too so strict returned-link validation recognizes it.

### Linux/macOS

Install the original core prerequisites and official cloudflared for your OS.
Start the original isolated PostgreSQL/Spring/EVM core per its environment-specific
configuration, then run from the checkout:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r django-service/requirements.txt -r tools/requirements-dev.txt
cloudflared --version
.venv/bin/python django-service/manage.py migrate --noinput
.venv/bin/python django-service/manage.py runserver 127.0.0.1:8000 --noreload
# In another terminal in the same checkout:
.venv/bin/python tools/share-tunnel.py status
.venv/bin/python tools/share-tunnel.py stop
```

The same `tools/share-tunnel.py start/status/stop/restart` CLI works. POSIX uses
`flock`; Windows uses byte-range locks. These OS startup/teardown paths have not
been exercised on Linux/macOS in this Windows run. Always use the orderly stop CLI;
Windows additionally uses a job object to kill the connector if its owner crashes.

## Architecture and security boundary

Private Django stays at loopback 8000; Spring 8080, EVM 8545 and PostgreSQL 55432
stay private. On the first public creation, an OS lock serializes startup across
private web workers. One detached supervisor holds a lifetime lock, serves a
separate Django profile through Waitress on 127.0.0.1:8001 and owns **one** reusable
cloudflared child. Local secret-authenticated control lives on 127.0.0.1:8002.
Receiver scans/GET requests do not start tunnels.

Only `/verify/<64-lowercase-hex-token>/`, session-bound
`/proof-status/<grant-UUID>/`, `/proof-download/<grant-UUID>/`, `/healthz/` and
the explicit CSS/JS/font allowlist exist publicly. `/`, admin/login/register,
wallet, sharing, integrity, API, original files and all other static files are
absent. A shared template preserves the original appearance without a private
home/navigation link. Public Django uses `DEBUG=False` and an exact active Host
check; the temporary hostname suffix allowance is confined to that process.

Waitress binds loopback, accepts only the loopback proxy's `X-Forwarded-Proto`,
sets the WSGI scheme and strips untrusted forwarded Host/IP/etc. Django doesn't
independently trust raw forwarding headers. Wrong Host is denied, non-HTTPS is
denied without redirect loops, CSRF accepts only the actual HTTPS form origin.
Cookies are distinct `__Host-` Secure/HttpOnly/SameSite=Lax cookies without Domain.
Public sessions/key/database are isolated under ignored `.local-data/receiver`;
released proof bundles remain encrypted in the existing session-cache format.
Static responses/errors also use no-store, strict-origin referrers, nosniff and
a CSP restricted to this receiver (no external RPC, trackers or frames).
The profile has no admin app or email backend. Its one-hour HSTS policy applies
only to the active hostname, without subdomain coverage or browser preloading.
`check --deploy` therefore reports the intentional `security.W005`/`W021`
warnings; the absent-mailer warning is explicitly silenced because there are no
mail routes. Local HTTP health is exempt from Django's redirect setting; all
other public HTTP requests are rejected by the boundary before any redirect.

Waitress caps request bodies at 16 KiB, headers at 8 KiB, connections at 64,
threads at eight and idle channels at 30 seconds. A thread-safe in-memory limiter
allows 12 POST/90 other dynamic requests per minute per Cloudflare-supplied IP,
with global 120/600 limits and bounded buckets; it stores only ephemeral salted
IP hashes and writes no personal-data log. Health probes also count at the public
edge; localhost health is available only at `/healthz/`. This is a demo limit,
not a distributed production abuse-control system. GET/HEAD/prefetch never calls
the release API. POST and any concurrent one-time release remain guarded by the
existing PostgreSQL grant lock; no retry/cache layer wraps disclosure opening.

The Quick Tunnel uses an isolated empty configuration instead of discovering or
modifying the user's `.cloudflared` configuration/credentials. A three-second
settling period precedes readiness probes; the installed CLI supports explicit
HTTP/2 transport, avoiding time spent on an unavailable UDP/QUIC path. Public
readiness requires HTTPS 200 and this receiver's exact health instance, never
just a printed hostname. Raw cloudflared output is consumed without being saved;
Django/Waitress request/error logging is suppressed in the receiver profile so
bearer paths, cookies/facts and exception traces are not logged. Control reports
only lifecycle metadata, sanitized errors, health codes and hostnames.
Private development request logs also suppress verify/status/export paths and
query strings, so previewing a bearer on the original local route cannot log it.

Spring constructs its share base at startup. Django validates the returned
internal origin and exact verification token path, then replaces only the origin
with the verified runtime hostname. Neither incoming Host nor user form data
selects the public base. The receipt/preview/copy/QR remain coherent. A second
health check precedes publication. If it fails after creation, Django attempts
to revoke that unpublished grant through the authenticated owner API; if revocation
is unavailable, the holder is told to revoke that grant on Shared before retrying.
An ambiguous backend create timeout also asks the holder to check Shared for a
new grant; a lost response cannot prove that the backend transaction rolled back.

## Receiver demo and limitations

1. Create a synthetic threshold-only proof. Show one fact disclosed/five withheld,
   an HTTPS temporary link, and the actual QR generated from it.
2. Scan on a **second phone with Wi-Fi disabled and mobile data enabled**. Merely
   viewing the landing must show no facts and must not consume a one-time grant.
3. Press **Open disclosed facts**. See only the authorized threshold, service
   verification and disclosed proof. Download in that browser; another session
   must receive 404 for the export. A second one-time opening must be denied.
4. Create a repeatable link, revoke it in the private Shared screen, and confirm
   future openings are denied. Confirm expiry similarly. Visit the private paths
   on the public origin and observe 404/403.
5. Create more shares and verify they reuse the active tunnel. Stop/restart using
   local controls; already sent Quick URLs/QRs stop working, new receipts use the
   new verified hostname. A live but unhealthy connector fails new sharing instead
   of rotating hosts silently. A dead owned connector can be replaced on a new share.

Independent **browser** EVM verification is deliberately disabled in the public
receiver, since the local chain RPC cannot be reached on another person's phone.
Service verification/downloads still work. Use the standalone original verifier
with a downloaded bundle, independently trusted pins and an explicitly reachable
trusted RPC if you want a separate cryptographic/chain check. Do not expose raw
Ganache to make the public button work. A passing proof shows platform-committed
membership and signature, not issuer truth or non-custodial holder authorization.

Bearer links can be forwarded; the intended-for label isn't authentication.
Revocation/expiry cannot erase already received facts/proofs. Cloudflare terminates
public TLS and can process the token-bearing paths and disclosed contents. Use
only test/synthetic records until your access/retention/privacy policy is reviewed.
[Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
are development tools: rotating hostnames, no uptime guarantee, 200 requests in
flight and no SSE. A stable [named tunnel](https://developers.cloudflare.com/tunnel/get-started/)
requires your own existing Cloudflare domain/account and provisioning.

## Repeatable checks

```powershell
Push-Location django-service
..\.venv\Scripts\python.exe manage.py test dashboard
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py check --settings=hermes.receiver_settings --deploy
Pop-Location
node --test tools/test-share-qr.cjs
npm run test:verifier
npm run test:contracts
.\spring-boot-service\mvnw.cmd -f spring-boot-service/pom.xml -B test
# These create/mutate only their own synthetic records in the isolated core:
.\.venv\Scripts\python.exe tools/test-live-workflow.py
.\.venv\Scripts\python.exe tools/test-live-security.py
# Intentionally stops/restarts this checkout's Quick Tunnel:
.\.venv\Scripts\python.exe tools/test-public-sharing.py
```

Public results record HTTP status/time in Asia/Kolkata and hostname-only evidence
under ignored `.local-data/cloudflare-public-results.json`. No tokens or facts are
written to its log. A physical mobile-data device, provisioned named tunnel and
Linux/macOS runtime require separate operator verification; a public URL test
from the holder computer must never be called a cellular test.

Official references checked: [Cloudflare ingress](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/configuration-file/),
[run parameters](https://developers.cloudflare.com/tunnel/reference/run-parameters/),
[Django 6.1](https://docs.djangoproject.com/en/6.1/ref/settings/),
[Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html).
