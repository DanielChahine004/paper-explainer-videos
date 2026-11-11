#!/bin/bash
cd "$(dirname "$0")/more"
for f in *.pdf; do [ -f "${f%.pdf}.txt" ] || ~/.pixi/bin/pixi exec -s poppler pdftotext -layout "$f" "${f%.pdf}.txt"; done
