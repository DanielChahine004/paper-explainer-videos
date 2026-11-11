#!/bin/bash
cd ~/slab_render/laser_rt
for s in Accelerators WhyParticles LWFA TNSA RPA UHDR Transport Future FieldMap; do
  if [ -f m_$s/videos/laser_vo/480p15/$s.mp4 ]; then echo "$s done"; else echo "$s rendering ($(tail -c 300 m_$s.log | tr '\n' ' ' | grep -o 'Animation [0-9]*' | tail -1))"; fi
done
grep -l -i "error\|Traceback" m_*.log 2>/dev/null
ps aux | grep -c "[m]anim"
date +%T
