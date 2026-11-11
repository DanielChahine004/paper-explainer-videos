#!/bin/bash
L="Block EnergyTime Normalise Cheaper FloodDOI Semi Takeaway"
cd ~/slab_render/calib && for s in $L; do rm -f m_$s/videos/calib_vo/480p15/$s.mp4; done
QUALITY=-ql JOBS=4 bash /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/tools/run_v.sh calib
bash /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/tools/sheet.sh calib calib_vo 480p15 /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/calib/src/sheets $L
