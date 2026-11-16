#!/bin/bash
L="Accelerators WhyParticles LWFA TNSA RPA UHDR Transport Future FieldMap"
cd ~/slab_render/laser_rt && for s in $L; do rm -f m_$s/videos/laser_vo/480p15/$s.mp4 m_$s/videos/laser_vo/1080p60/$s.mp4; done
QUALITY=-ql JOBS=5 bash /home/h/Code/paper-explainer-videos/tools/run_v.sh laser_rt
grep -h "best take only" m_*.log | head
bash /home/h/Code/paper-explainer-videos/tools/sheet.sh laser_rt laser_vo 480p15 /home/h/Code/paper-explainer-videos/laser_rt/src/sheets $L
