export PATH=$HOME/.pixi/bin:$PATH
cd ~/slab_render/laser_rt
f=m_WhyParticles/videos/laser_vo/1080p60/WhyParticles.mp4
d=$(pixi run ffprobe -v error -show_entries format=duration -of csv=p=0 $f)
s=$(python3 -c "print($d*0.60)")
pixi run ffmpeg -loglevel error -y -ss $s -t 9 -i $f -vf "fps=4/3,scale=480:-1,tile=4x3" -frames:v 1 /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/laser_rt/src/sweep.png
echo $f $d
