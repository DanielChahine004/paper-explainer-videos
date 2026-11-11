#!/bin/bash
cd "$(dirname "$0")"; P=~/.pixi/bin/pixi
$P exec -s poppler pdftoppm -png -r 70 -f 6 -l 6 -singlefile Freire2026.pdf pv_F26_6
