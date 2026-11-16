#!/bin/bash
L="EnergyWhy EnergyHow Drift TimingWhy TimingHow NormWhy NormHow Upkeep"
QUALITY=-ql JOBS=2 bash /home/h/Code/paper-explainer-videos/tools/run_v.sh calib
bash /home/h/Code/paper-explainer-videos/tools/sheet.sh calib calib_vo 480p15 /home/h/Code/paper-explainer-videos/calib/src/sheets $L
