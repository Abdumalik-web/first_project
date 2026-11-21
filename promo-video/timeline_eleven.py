# Builds timeline for the ElevenLabs voice: cuts the 7 ad phrases (first 16.45s of the file),
# maps scene boundaries to the pauses, writes build/voice.wav + build/timeline.json.
import json, subprocess, glob
SRC = glob.glob("ElevenLabs_*.mp3")[0]
LEAD = 0.25          # voice starts at 0.25s in the video
CUT = 16.45          # end of the ad script in the source file
DUR = 17.3           # final video length
# source-time phrase spans (from silencedetect)
PH = [(0.00,1.07,"Haydovchimisiz?"),(1.47,3.14,"Yoki yoʻlovchimisiz?"),
      (3.48,4.81,"Unda bu siz uchun!"),(5.23,7.84,"Botimiz haydovchi va yoʻlovchilarni birlashtiradi."),
      (8.18,12.01,"Manzilingizga tez yeting, chegirma va bonuslarga ega boʻling!"),
      (12.27,14.49,"Batafsil maʼlumot — Telegram sahifamizda."),(14.74,16.33,"Hoziroq qoʻshiling!")]
# scene boundaries in the middle of pauses (source time) -> real time
B = [3.31, 8.01, 12.14]
real = [0] + [b+LEAD for b in B] + [DUR]
orig = [0, 3.05, 6.85, 10.75, 15.0]          # boundaries the animation was designed for
subs = [dict(a=round(a+LEAD,3), b=round(b+LEAD,3), text=t) for a,b,t in PH]
json.dump(dict(dur=DUR, real=real, orig=orig, subs=subs), open("build/timeline.json","w"), ensure_ascii=False, indent=1)
subprocess.run(["ffmpeg","-v","error","-y","-i",SRC,"-t",str(CUT),"-af",
  f"afade=t=out:st={CUT-0.12}:d=0.12,adelay={int(LEAD*1000)},apad=whole_dur={DUR}","-ar","44100","-ac","1","build/voice.wav"],check=True)
print(json.dumps(dict(real=real), indent=0))
