#!/usr/bin/env bash
# Rebuilds yoldamiz_reklama_15s.mp4: expressive female Uzbek voice (edge-tts, Madina) + animation + music.
# Needs: pip install edge-tts numpy, ffmpeg, node + playwright. Edit phrases/intonation in voice.py.
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p build
python3 voice.py        # phrase clips with per-phrase pitch/rate/pauses
python3 voicetrack.py   # timeline -> build/voice.wav + build/subs.json
python3 music.py        # background music -> build/music.wav
node render.js video    # animation frames -> build/video.mp4 (subtitles from subs.json)
ffmpeg -v error -y -i build/video.mp4 -i build/music.wav -i build/voice.wav -filter_complex "
[2]highpass=f=80,acompressor=threshold=-20dB:ratio=2.5,volume=1.7,asplit=2[voice][sc];
[1]aresample=44100,volume=0.45[mus];[mus][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[duck];
[voice][duck]amix=inputs=2:normalize=0,alimiter=limit=0.95,apad[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -shortest yoldamiz_reklama_15s.mp4
echo "done: yoldamiz_reklama_15s.mp4"

# --- ElevenLabs version (uses ElevenLabs_*.mp3 in this folder; video becomes 17.3s) ---
# python3 timeline_eleven.py && python3 music.py && node render.js video && <same ffmpeg mix> -> yoldamiz_reklama_elevenlabs.mp4
# Delete build/timeline.json to go back to the 15s Madina version.
