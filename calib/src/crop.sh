#!/bin/bash
cd "$(dirname "$0")"; P="$HOME/.pixi/bin/pixi exec -s poppler pdftoppm -png -r 300 -singlefile"
$P -f 17 -l 17 -x 493 -y 1475 -W 1480 -H 810 Borghi2016.pdf ../assets/borghi_fig7
$P -f 18 -l 18 -x 686 -y 1360 -W 1225 -H 820 Borghi2016.pdf ../assets/borghi_fig9
$P -f 6 -l 6 -x 514 -y 296 -W 1500 -H 505 Freire2026.pdf ../assets/db_fanbeam
$P -f 7 -l 7 -x 530 -y 398 -W 520 -H 497 Freire2026.pdf ../assets/db_normphantom
ls ../assets
