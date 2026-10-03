# Foliolet frontend

Django 6.1 provides the holder wallet, enrollment/review, disclosure composer, sharing receipts, integrity pairing and public verifier. It forwards owner actions to Spring through `wallet_api.py`; wallet routes always use the real API and do not fabricate successful data. SQLite holds Django server-side sessions only; PostgreSQL remains the document system of record.

Run `tools/start-frontend.ps1` from the repository root after installing the root virtual environment; see [complete guide](../docs/RUN_GUIDE.md). `PRODUCT_LABEL` defaults to Foliolet and remains configurable. `SPRING_BOOT_API_BASE_URL` and `PUBLIC_EVM_RPC_URL` configure the backend bridge and independent browser RPC respectively.

The interface follows [DESIGN.md](../DESIGN.md): tokens and components live in `dashboard/static/wallet/wallet.css`, shared partials are the `wallet/_*.html` templates, and display vocabulary is in `templatetags/wallet_ui.py`. Screens at desktop and phone widths are in [docs/screenshots/redesign](../docs/screenshots/redesign/).

Static proof/QR dependencies are bundled locally with licenses; rebuild them using root `npm run assets:build`. Browser verification recomputes Merkle/signature encodings and reads Solidity directly. It requires trusted registry/operator/chain pins; service link policy is shown separately.

`manage.py test dashboard` runs nineteen UI boundary and security regression tests. `manage.py check` validates configuration. Actual browser sign-in/enrollment/sharing/direct verification and real backend/EVM integration are recorded in [validation](../docs/VALIDATION.md).

Legacy screens are preserved under `/legacy/` only if `ENABLE_LEGACY_UI=true`; the default UI contains no legal/case management surface. See [security](../docs/SECURITY.md) before any nonlocal deployment.

`WALLET_TRUST_FILE` points to separately provisioned registry/operator/chain pins (default `.local-data/trusted-deployment.json`). No Spring discovery fallback exists. Run `manage.py migrate` to remove legacy plaintext suggestion copies; current suggestions are transient authenticated responses from the encrypted original.
