# Places voice phrases on the timeline -> build/voice.wav and build/subs.json (read by render.js)
import json, wave, numpy as np
SR=44100; DUR=15.0
SCENE_START={1:0.45, 2:3.2, 3:7.05, 4:10.95}
ph=json.load(open("build/ph/phrases.json")); track=np.zeros(int(SR*DUR)); subs=[]; cur={}
for p in ph:
    t=cur.get(p["scene"], SCENE_START[p["scene"]])
    with wave.open(p["wav"]) as w: a=np.frombuffer(w.readframes(w.getnframes()),np.int16)/32768
    s=int(t*SR); track[s:s+len(a)]+=a[:len(track)-s]
    subs.append(dict(a=round(t,3), b=round(t+p["dur"],3), text=p["text"]))
    cur[p["scene"]]=t+p["dur"]+p["pause"]
with wave.open("build/voice.wav","wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(track,-1,1)*32767).astype(np.int16).tobytes())
json.dump(subs, open("build/subs.json","w"), ensure_ascii=False, indent=1)
for s in subs: print(s)
