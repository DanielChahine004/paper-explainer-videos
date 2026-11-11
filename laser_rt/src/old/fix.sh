# Re-render only the two scenes vlint fixed (intro-and-pulse), trusting the other 1080p scenes as rendered.
export PATH="$HOME/.pixi/bin:$PATH"
SRC=/mnt/c/Users/h/Desktop/slab_crlb_narrated_project
cd ~/slab_render
cp $SRC/common.py $SRC/voices.py . && rm -rf tools && cp -r $SRC/tools . && find tools -name "*.sh" -exec sed -i 's/\r$//' {} +
cp $SRC/laser_rt/laser_vo.py $SRC/laser_rt/render.sh laser_rt/ && sed -i 's/\r$//' laser_rt/render.sh
cd laser_rt
pixi run python ../tools/vlint adopt . --script laser_vo.py --res 1080p60 Opening WhyParticles Overview LWFA RPA Compare BeamTime BeamYield UHDR Transport SOBP Biology Challenges Future Takeaway FieldMap
QUALITY=-qh JOBS=2 bash render.sh 2>&1 | grep -E "== |done|FAILED|error\[|warn\[|vlint:|wrote"
cp laser_rt_explainer_narrated.mp4 $SRC/laser_rt/
pixi run ffmpeg -loglevel error -y -i laser_rt_explainer_narrated.mp4 -c:v libx264 -crf 26 -preset slow -c:a aac -b:a 128k -movflags +faststart $SRC/laser_rt/laser_rt_explainer_small.mp4
ls -la $SRC/laser_rt/*.mp4
bash $SRC/tools/sheet.sh laser_rt laser_vo 1080p60 $SRC/laser_rt/src/sheets_fix Accelerators TNSA
