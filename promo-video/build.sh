#!/usr/bin/env bash
# Rebuilds yoldamiz_reklama_15s.mp4: neural Uzbek voice (edge-tts) + animation + music.
# Needs: pip install edge-tts, ffmpeg, node + playwright, python3 + numpy.
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p build
LINES=("Haydovchimisiz yoki yo‘lovchimisiz?" "Botimiz haydovchi va yo‘lovchilarni birlashtiradi." \
       "Manzilingizga yeting, chegirma va bonuslar oling!" "Batafsil Telegram sahifamizda. Hoziroq qo‘shiling!")
for i in 1 2 3 4; do
  edge-tts ${HTTPS_PROXY:+--proxy "$HTTPS_PROXY"} --voice uz-UZ-SardorNeural --rate=-5% --text "${LINES[$((i-1))]}" --write-media build/n$i.mp3
  ffmpeg -v error -y -i build/n$i.mp3 -af "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse" -ar 44100 build/nseg$i.wav
done
python3 music.py
node render.js video
# voice offsets (ms) must match SUBS timings in scene.html
ffmpeg -v error -y -i build/video.mp4 -i build/music.wav -i build/nseg1.wav -i build/nseg2.wav -i build/nseg3.wav -i build/nseg4.wav -filter_complex "
[2]adelay=450|450[v1];[3]adelay=3350|3350[v2];[4]adelay=7150|7150[v3];[5]adelay=11050|11050[v4];
[v1][v2][v3][v4]amix=inputs=4:normalize=0,highpass=f=80,acompressor=threshold=-20dB:ratio=2.5,volume=1.6,asplit=2[voice][sc];
[1]aresample=44100,volume=0.5[mus];[mus][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[duck];
[voice][duck]amix=inputs=2:normalize=0,alimiter=limit=0.95,apad[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -shortest yoldamiz_reklama_15s.mp4
echo "done: yoldamiz_reklama_15s.mp4"
