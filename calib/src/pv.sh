#!/bin/bash
cd "$(dirname "$0")"; P=~/.pixi/bin/pixi
for k in Borghi2016; do n=$($P exec -s poppler pdfinfo $k.pdf | awk '/Pages/{print $2}'); for ((i=1;i<=n;i++)); do $P exec -s poppler pdftotext -f $i -l $i $k.pdf - | grep -o -E "^ *Figure [0-9]+\. .{0,90}" | sed "s/^/$k p$i: /"; done; done
$P exec -s poppler pdftoppm -png -r 60 -f 7 -l 7 -singlefile Freire2026.pdf pv_F26_7
