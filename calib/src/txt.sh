#!/bin/bash
cd "$(dirname "$0")"
for f in *.pdf; do ~/.pixi/bin/pixi exec -s poppler pdftotext -layout "$f" "${f%.pdf}.txt"; done
for f in *.txt; do echo "== $f $(wc -l < $f)"; grep -i -m3 -E "creative commons|CC BY|open access|rights reserved|copyright" "$f"; done
