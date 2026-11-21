# Uses an uploaded ElevenLabs take (ElevenLabs_*.mp3 in this folder) instead of the placeholder voice.
# Splits it into the 10 script phrases at the 9 longest pauses, keeps the natural timing,
# and writes build/voice.wav + build/timeline.json (scenes follow the voice).
import glob, json, re, subprocess, sys
SEGS=[1,1,2,3,3,4,4,5,5,6]
TEXT=["Fargʻonadan Toshkentgami?","Yoki Toshkentdan Fargʻonagami?","Taksi qidirib qoʻngʻiroq qilishdan charchadingizmi?",
 "Botimizga bir daqiqada soʻrov qoldiring.","Bot sizga eng yaqin haydovchini oʻzi topadi!","Haydovchimisiz?",
 "Boʻsh joy bilan yurmaysiz, yoʻlovchilar sizni oʻzi topadi!","Yoʻlovchi uzating — oʻn ming soʻm!",
 "Doʻstingizni taklif qiling — besh ming soʻm!","Botga kiring, start bosing va boshladik!"]
src=sys.argv[1] if len(sys.argv)>1 else sorted(glob.glob("ElevenLabs_*"))[-1]
LEAD=0.3; TAIL=1.3
total=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",src]))
log=subprocess.run(["ffmpeg","-hide_banner","-i",src,"-af","silencedetect=n=-40dB:d=0.12","-f","null","-"],capture_output=True,text=True).stderr
st=[float(x) for x in re.findall(r"silence_start: ([\d.]+)",log)]; en=[float(x) for x in re.findall(r"silence_end: ([\d.]+)",log)]
sil=list(zip(st,en+[total]*(len(st)-len(en))))
head=sil[0][1] if sil and sil[0][0]<0.05 else 0.0
tail=sil[-1][0] if sil and sil[-1][1]>=total-0.05 else total
inner=[s for s in sil if s[0]>head+0.05 and s[1]<tail-0.05]
if len(inner)<9: sys.exit(f"Only {len(inner)+1} phrases found; expected 10. Check the recording.")
cuts=sorted(sorted(inner,key=lambda s:s[1]-s[0],reverse=True)[:9])
spans=[]; a=head
for s,e in cuts: spans.append((a,s)); a=e
spans.append((a,tail))
off=LEAD-head; DUR=round(tail+off+TAIL,2)
subs=[dict(a=round(a+off,3),b=round(b+off,3),text=TEXT[i]) for i,(a,b) in enumerate(spans)]
bounds=[0]
for i in range(1,10):
    if SEGS[i]!=SEGS[i-1]: bounds.append(round((spans[i-1][1]+spans[i][0])/2+off,3))
bounds.append(DUR)
segments=[dict(id=k+1,start=bounds[k],end=bounds[k+1]) for k in range(6)]
subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-ss",str(head),"-to",str(tail),"-af",f"adelay={int(LEAD*1000)},apad=whole_dur={DUR}","-ar","44100","-ac","1","build/voice.wav"],check=True)
json.dump(dict(dur=DUR,segments=segments,subs=subs),open("build/timeline.json","w"),ensure_ascii=False,indent=1)
print("source:",src,"| video length:",DUR); [print(s) for s in subs]
