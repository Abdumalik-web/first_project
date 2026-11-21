#!/usr/bin/env bash
# Mix build/video.mp4 + build/music.wav + build/voice.wav -> yoldamiz_3d_22s.mp4
set -e; cd "$(dirname "$0")"
ffmpeg -v error -y -i build/video.mp4 -i build/music.wav -i build/voice.wav -filter_complex "
[2]highpass=f=70,acompressor=threshold=-20dB:ratio=2.5,volume=1.6,asplit=2[voice][sc];
[1]aresample=44100,volume=0.45[mus];[mus][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[duck];
[voice][duck]amix=inputs=2:normalize=0,alimiter=limit=0.95,apad[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -shortest ${1:-yoldamiz_3d_22s.mp4}
