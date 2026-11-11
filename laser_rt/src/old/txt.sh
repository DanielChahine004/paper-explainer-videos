#!/bin/bash
cd "$(dirname "$0")"; P=~/.pixi/bin/pixi
$P exec -s poppler pdftotext -layout paper.pdf paper.txt
$P exec -s poppler pdfinfo paper.pdf | grep -E "Pages|Title"
wc -l paper.txt
grep -i -m4 -E "creative commons|CC BY|rights reserved|open access|copyright" paper.txt
