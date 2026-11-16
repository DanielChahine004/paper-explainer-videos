#!/bin/bash
pkill -f "manim.*laser_vo.py" 2>/dev/null; sleep 2
L="Accelerators TNSA Transport FieldMap"
cd ~/slab_render/laser_rt && for s in $L; do rm -f m_$s/videos/laser_vo/480p15/$s.mp4; done
QUALITY=-ql JOBS=4 bash /home/h/Code/paper-explainer-videos/tools/run_v.sh laser_rt
bash /home/h/Code/paper-explainer-videos/tools/sheet.sh laser_rt laser_vo 480p15 /home/h/Code/paper-explainer-videos/laser_rt/src/sheets Accelerators WhyParticles LWFA TNSA RPA UHDR Transport Future FieldMap
