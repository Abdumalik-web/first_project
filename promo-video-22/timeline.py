# Places phrases on the timeline -> build/voice.wav + build/timeline.json (segments, subs, duration)
import json, wave, numpy as np
SR=44100; LEAD=0.3; GAP=0.3; TAIL=1.3
ph=json.load(open("build/ph/phrases.json")); t=LEAD; subs=[]; segs={}; clips=[]
for i,p in enumerate(ph):
    if i>0 and p["seg"]!=ph[i-1]["seg"]: t+=GAP
    segs.setdefault(p["seg"],[t,0]); subs.append(dict(a=round(t,3),b=round(t+p["dur"],3),text=p["text"]))
    clips.append((t,p["wav"])); t+=p["dur"]; segs[p["seg"]][1]=t; t+=p["pause"]
DUR=round(t+TAIL,2)
ids=sorted(segs); bounds=[0]+[round((segs[ids[k-1]][1]+segs[ids[k]][0])/2,3) for k in range(1,len(ids))]+[DUR]
segments=[dict(id=ids[k],start=bounds[k],end=bounds[k+1]) for k in range(len(ids))]
tr=np.zeros(int(SR*DUR))
for st,w in clips:
    with wave.open(w) as f: a=np.frombuffer(f.readframes(f.getnframes()),np.int16)/32768
    s=int(st*SR); tr[s:s+len(a)]+=a[:len(tr)-s]
with wave.open("build/voice.wav","wb") as f:
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes((np.clip(tr,-1,1)*32767).astype(np.int16).tobytes())
json.dump(dict(dur=DUR,segments=segments,subs=subs),open("build/timeline.json","w"),ensure_ascii=False,indent=1)
print("DUR",DUR); [print(s) for s in segments]
