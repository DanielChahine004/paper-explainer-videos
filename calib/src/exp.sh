#!/bin/bash
L="EnergyWhy EnergyHow Drift TimingWhy TimingHow NormWhy NormHow Upkeep"
QUALITY=-ql JOBS=2 bash /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/tools/run_v.sh calib
bash /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/tools/sheet.sh calib calib_vo 480p15 /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/calib/src/sheets $L
