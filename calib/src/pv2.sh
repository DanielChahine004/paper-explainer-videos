#!/bin/bash
cd "$(dirname "$0")"; P=~/.pixi/bin/pixi
for p in 17 18; do $P exec -s poppler pdftoppm -png -r 70 -f $p -l $p -singlefile Borghi2016.pdf pv_B_$p; done
