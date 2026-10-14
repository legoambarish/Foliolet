# Receiver-only Cloudflare plan, 14 October 2026

Base: Foliolet `origin/main` b810d2a07a1e2aec9a9fc4d8a8c2d1aaaec2b5f2, fetched from
https://github.com/legoambarish/Foliolet.git. Branch: `testcloudflare`, separate
worktree `C:/Users/User/Downloads/Foliolet-testcloudflare`. Original checkout is
on `codex/foliolet-evidence-bridge` with untracked documentation/output. It stays
untouched. Local `main` is legacy upstream c04741ee68563566dc82ab4e71b97c3898714f72
and is deliberately not updated. No push, PR, merge or previous redesign code.

## Baseline traced from this base

1. Authenticated `dashboard/wallet_views.py:compose` posts selected claim IDs and
   existing terms to Spring `/api/wallet/disclosures`.
2. `DisclosureService.create` locks the credential, checks current source/chain,
   creates the existing encrypted grant and returns startup-configured
   `wallet.share-base-url` + `/verify/<64 lowercase hex token>/`.
3. `share_ready.html` puts that URL in `#share-url` and preview. `wallet.js` copies
   that value and passes the identical value to the bundled QR generator.
4. `wallet_views.verify` GET is a landing only. POST with Django CSRF calls Spring
   `/api/public/disclosures/<token>/open`. Spring locks the grant, enforces
   expiry/revocation/one-time/source freshness and verifies the signed proof.
5. Django validates the response and encrypts the released bundle in its session
   for export. Download revalidates current policy without opening again. Status
   calls the internal Spring status API. `verify.js` optionally reads an EVM RPC
   directly; its default loopback RPC is unusable on another person's phone.
6. `hermes.urls` includes admin/private wallet routes: it cannot be the public
   origin. `wallet/base.html` currently reverses a private home link even in
   receiver mode, so it needs one surgical public-header fix.

Baseline checks: Django 27 tests PASS; Maven package 25 tests PASS. No retained
data/config from the previous implementation is used. Live checks will use new
synthetic accounts, isolated PostgreSQL, vault, EVM and Django session data here.

## Implementation and boundary

- Add public settings/URLconf with only verify, session-bound proof status and
  download, minimal health and an explicit static asset allowlist. Waitress binds
  loopback 8001, DEBUG=False, separate receiver cookies/key/session DB, strict
  active-host validation, trusted loopback TLS forwarding, CSRF, no-store,
  origin-only referrer, restricted CSP, bounded bodies and rate limiting.
- One detached local supervisor owns the Waitress receiver and one cloudflared
  child. Cross-process file locks serialize startup; a secret-protected loopback
  control service supports health/start/stop. Requests have bounded timeouts.
  Public health carries only a random instance marker to prove a public hostname
  reaches this exact restricted origin. Unavailable/restarted tunnels are never
  advertised from stale metadata. No management route is on the public URLconf.
- Quick mode is default, local mode explicit. Named mode connects an already
  provisioned operator-managed tunnel to this receiver and verifies its hostname;
  it performs no account, credential, DNS or other Cloudflare administration.
- Before grant creation ensure public health; then strictly validate the backend
  URL/token and replace its origin. Recheck availability before publication. If
  publication fails after creation, attempt owner-authenticated revocation and
  report any unresolved grant for the holder to revoke. Do not restart Spring or
  change grant semantics. Keep preview/copy/QR tied to the same field.
- Preserve appearance; label temporary/local/stable origins and outage behavior.
  Public independent browser chain checking is disabled with an honest downloaded
  proof explanation. Raw local RPC and backend remain private.
- Add lifecycle/concurrency/URL/security tests; exercise live public HTTPS GET,
  POST, session download, one-time race, expiry/revocation, blocked private routes,
  static/cookies/CSRF, tunnel reuse/death/restart and existing regression suites.
  A physical second cellular device may be unavailable and will be reported as
  untested instead of equating same-host public HTTPS with a separate network.

## Sources checked before implementation

- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/):
  no account/domain, temporary hostname, no uptime guarantee, 200 requests in
  flight, no SSE. Current docs also describe optional email gating, which is
  outside this bearer-link integration.
- [Tunnel setup](https://developers.cloudflare.com/tunnel/get-started/) and
  [local ingress](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/configuration-file/):
  stable domain requires an existing Cloudflare zone; local ingress ends in 404.
- [Local tunnel setup](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/).
- [Django 6.1 settings](https://docs.djangoproject.com/en/6.1/ref/settings/), matching
  installed/pinned Django. Trust forwarding only at the loopback proxy boundary.
- [Waitress arguments](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html):
  Windows-compatible WSGI; trust only selected proxy headers, clear other headers,
  restrict request size. New dependency is Waitress only; no unrelated upgrades.

Cloudflare terminates HTTPS and can see bearer URL paths and disclosed contents.
Only synthetic documents will be used in live exposure testing.
