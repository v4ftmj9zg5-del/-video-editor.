#!/usr/bin/env bash
# Render every client-kit HTML page to PDF with headless Chromium.
# Usage: tools/client_kit/build.sh OUT_DIR
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="${1:?usage: build.sh OUT_DIR}"
mkdir -p "$out"
chrome="${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"
for f in "$here"/[0-9][0-9]_*.html; do
  name="$(basename "$f" .html)"
  "$chrome" --headless --no-sandbox --disable-gpu --allow-file-access-from-files \
    --no-pdf-header-footer --run-all-compositor-stages-before-draw --virtual-time-budget=5000 \
    --print-to-pdf="$out/$name.pdf" "file://$f" 2>/dev/null
  echo "wrote $out/$name.pdf"
done
