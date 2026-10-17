#!/usr/bin/env bash
# Screenshot the offline preview with a headless Chrome. Usage:
#   CHROME=/path/to/chrome-headless-shell tools/frontend-preview/shoot.sh http://127.0.0.1:8772 OUT_DIR [light|dark]
# Viewport-only shots at desktop, tablet and phone sizes. Talks only to the preview URL given.
set -euo pipefail
BASE="$1"; OUT="$2"; SCHEME="${3:-light}"
mkdir -p "$OUT"
# Blink colour-scheme override: 0 = dark, 1 = light.
PREF=$([ "$SCHEME" = dark ] && echo 0 || echo 1)
PAGES=(
  "home|/"
  "home-search|/search/"
  "home-first-run|/first-run/"
  "enroll|/wallet/enroll/"
  "detail-draft|/wallet/doc-draft-7f2a/"
  "detail-active|/wallet/doc-active-31c9/"
  "detail-revoked|/wallet/doc-revoked-0b44/"
  "compose|/wallet/doc-active-31c9/share/"
  "sharing|/sharing/"
  "share-ready|/sharing/ready/"
  "integrity|/integrity/"
  "ask-foli|/ask-foli/"
  "signature|/wallet/doc-active-31c9/signature/"
  "login|/login/"
  "register|/register/"
  "verify|/verify/demo-token/"
  "verify-gate|/verify/gate-token/"
)
SIZES=("desktop|1440,900" "tablet|834,1112" "phone|390,844")
for page in "${PAGES[@]}"; do
  name="${page%%|*}"; path="${page#*|}"
  for size in "${SIZES[@]}"; do
    label="${size%%|*}"; dims="${size#*|}"
    "$CHROME" --headless --no-sandbox --in-process-gpu --user-data-dir="$OUT/.chrome-profile" --hide-scrollbars --no-first-run --no-default-browser-check \
      --blink-settings=preferredColorScheme=$PREF --force-device-scale-factor=1 \
      --virtual-time-budget=2500 --window-size="$dims" \
      --screenshot="$OUT/${name}-${label}-${SCHEME}.png" "$BASE$path" >/dev/null 2>&1 || echo "failed: $name $label"
  done
done
echo "shots in $OUT"
