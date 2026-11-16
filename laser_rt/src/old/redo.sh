#!/bin/bash
L="LWFA TNSA BeamYield UHDR Transport Future Takeaway"
cd ~/slab_render/laser_rt && for s in $L; do rm -f m_$s/videos/laser_vo/480p15/$s.mp4; done
QUALITY=-ql JOBS=4 bash /home/h/Code/paper-explainer-videos/tools/run_v.sh laser_rt
bash /home/h/Code/paper-explainer-videos/tools/sheet.sh laser_rt laser_vo 480p15 /home/h/Code/paper-explainer-videos/laser_rt/src/sheets $L
