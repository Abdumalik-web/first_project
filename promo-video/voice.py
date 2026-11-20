# Generates expressive female Uzbek voiceover phrase by phrase (uz-UZ-MadinaNeural).
# Each line: (scene, text, rate, pitch, volume, pause_after_s)
import asyncio, os, subprocess, json, edge_tts
V = "uz-UZ-MadinaNeural"
PHRASES = [
  (1, "Haydovchimisiz?",                     "+0%",  "+12Hz", "+0%", 0.25),
  (1, "Yoki yoʻlovchimisiz?",                "+0%",  "+16Hz", "+0%", 0.0),
  (2, "Unda bu siz uchun!",                  "+5%",  "+8Hz",  "+0%", 0.2),
  (2, "Botimiz haydovchi va yoʻlovchilarni birlashtiradi.", "+6%", "+0Hz", "+0%", 0.0),
  (3, "Manzilingizga tez yeting,",           "+4%",  "+6Hz",  "+0%", 0.18),
  (3, "chegirma va bonuslarga ega boʻling!", "+6%",  "+14Hz", "+5%", 0.0),
  (4, "Batafsil maʼlumot — Telegram sahifamizda.", "+4%", "+2Hz", "+0%", 0.3),
  (4, "Hoziroq qoʻshiling!",                 "+0%",  "+18Hz", "+10%", 0.0),
]
TRIM = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"
def dur(p): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]))
async def main():
    os.makedirs("build/ph", exist_ok=True); out=[]
    for i,(sc,txt,r,p,vol,pause) in enumerate(PHRASES):
        mp3=f"build/ph/p{i}.mp3"; wav=f"build/ph/p{i}.wav"
        await edge_tts.Communicate(txt, V, rate=r, pitch=p, volume=vol, proxy=os.environ.get("HTTPS_PROXY")).save(mp3)
        subprocess.run(["ffmpeg","-v","error","-y","-i",mp3,"-af",TRIM,"-ar","44100","-ac","1",wav],check=True)
        out.append(dict(scene=sc,text=txt,wav=wav,dur=round(dur(wav),3),pause=pause))
    json.dump(out, open("build/ph/phrases.json","w"), ensure_ascii=False, indent=1)
    for s in range(1,5):
        tot=sum(o["dur"]+o["pause"] for o in out if o["scene"]==s); print("scene",s,round(tot,2),"s")
asyncio.run(main())
