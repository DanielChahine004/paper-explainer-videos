#!/bin/bash
cd ~/slab_render/laser_rt
for s in Accelerators TNSA Transport FieldMap; do echo "== $s"; grep -a -E "^[A-Za-z]*Error|Error:|Exception" m_$s.log | tail -2; grep -a -c "voiceover" m_$s.log; done
