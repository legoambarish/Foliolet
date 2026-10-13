# NFC discovery and offline checklist

Physical NFC: NOT TESTED. No tag or compatible reader was available. Ordinary NTAG213/215/216 stickers can be cloned and may remain rewritable. No secure-element or dynamic challenge claim is made.

For a voluntary operator demonstration, run the restricted public preview and use an HTTPS URL under an explicitly authorized public hostname. With a phone NFC writing app, create an NDEF URL record pointing to `/discover/`, write it to the sticker, leave it rewritable, and test the same URL as a printed QR fallback. Never put a grant token, document bytes, wallet key or sensitive identifier in the tag. The discovery page directs the verifier to create a fresh signed request; the holder still reviews and signs the exact disclosure in her private session. A cloned tag gives no extra authority.

The tunnel manager is disabled until `--opt-in-exposure` is explicitly supplied. It targets only port 8001, starts when the local governance endpoint reports live grants, and stops when none remain or the state becomes unavailable. It was not run externally in this implementation. Cloudflare terminates TLS and can observe disclosed facts. URL-fragment encryption was cut; do not represent this path as end-to-end encrypted. A quick tunnel hostname is transient; a live Setu callback requires an independently configured stable HTTPS base URL.

Before a phone-hotspot or disconnected demonstration:

- Cache Python, Maven and Node dependencies, the PostgreSQL tools and optional model weights while online.
- Run native launch and `rehearse-bridge.ps1 -ProveOffline` in advance. Keep independent pins separate from packages.
- Charge the laptop, disable sleep for the demonstration, and retain encrypted holder backups.
- Warm qwen3:4b last, or run manual approval without AI. Cold model startup can exceed the UI timeout.
- Keep loopback binding as the default. A phone cannot reach `127.0.0.1` on the laptop. Phone access requires an explicit exposure decision and configured host/network routing; it is not silently enabled by hotspot use.
- Keep the chain running for current reliance. With the chain stopped, show UNKNOWN. Historical reproduction also needs the recorded chain state; there is no fabricated offline chain oracle.
- Keep the labeled backup script and prior captures available. State which checks are recorded rather than live.
