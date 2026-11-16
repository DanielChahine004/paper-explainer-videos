#!/bin/bash
L="Block EnergyTime Normalise Cheaper FloodDOI Semi Takeaway"
cd ~/slab_render/calib && for s in $L; do rm -f m_$s/videos/calib_vo/480p15/$s.mp4; done
QUALITY=-ql JOBS=4 bash /home/h/Code/paper-explainer-videos/tools/run_v.sh calib
bash /home/h/Code/paper-explainer-videos/tools/sheet.sh calib calib_vo 480p15 /home/h/Code/paper-explainer-videos/calib/src/sheets $L
