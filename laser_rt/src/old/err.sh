#!/bin/bash
grep -a -E "Error|error:|Exception" ~/slab_render/laser_rt/m_Biology.log | tail -4
