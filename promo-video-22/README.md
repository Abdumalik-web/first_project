# Yoʻldamiz — 22s 3D promo (Instagram Reels, 1080×1920)

- `yoldamiz_3d_22s.mp4` — final video
- `index.html` + `main.js` — three.js scenes (shots are timed from `build/timeline.json`)
- `voice.py` → `timeline.py` — placeholder voice (edge-tts) and timeline
- `eleven.py` — use an uploaded `ElevenLabs_*.mp3` instead (splits it into the 10 phrases)
- `music.py`, `render.js`, `mix.sh`

Rebuild with ElevenLabs voice:
```
npm i && python3 eleven.py && python3 music.py && node render.js video && ./mix.sh
```
