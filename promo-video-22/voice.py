# Placeholder voice (edge-tts Madina) phrase by phrase -> build/ph/*.wav + build/ph/phrases.json
import asyncio, os, subprocess, json, edge_tts
V="uz-UZ-MadinaNeural"
# (segment, text, rate, pitch, volume, pause_after)
PH=[(1,"Fargʻonadan Toshkentgami?","+0%","+12Hz","+0%",0.2),
    (1,"Yoki Toshkentdan Fargʻonagami?","+0%","+16Hz","+0%",0),
    (2,"Taksi qidirib qoʻngʻiroq qilishdan charchadingizmi?","-3%","+4Hz","+0%",0),
    (3,"Botimizga bir daqiqada soʻrov qoldiring.","+5%","+2Hz","+0%",0.15),
    (3,"Bot sizga eng yaqin haydovchini oʻzi topadi!","+5%","+10Hz","+0%",0),
    (4,"Haydovchimisiz?","+0%","+14Hz","+0%",0.15),
    (4,"Boʻsh joy bilan yurmaysiz, yoʻlovchilar sizni oʻzi topadi!","+6%","+8Hz","+0%",0),
    (5,"Yoʻlovchi uzating — oʻn ming soʻm!","+4%","+14Hz","+5%",0.15),
    (5,"Doʻstingizni taklif qiling — besh ming soʻm!","+4%","+14Hz","+5%",0),
    (6,"Botga kiring, start bosing va boshladik!","+2%","+18Hz","+10%",0)]
TRIM="silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"
dur=lambda p: float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]))
async def main():
    os.makedirs("build/ph",exist_ok=True); out=[]
    for i,(sg,tx,r,p,v,pa) in enumerate(PH):
        mp3=f"build/ph/p{i}.mp3"; wav=f"build/ph/p{i}.wav"
        r=f"{int(r[:-1])+9:+d}%"
        await edge_tts.Communicate(tx,V,rate=r,pitch=p,volume=v,proxy=os.environ.get("HTTPS_PROXY")).save(mp3)
        subprocess.run(["ffmpeg","-v","error","-y","-i",mp3,"-af",TRIM,"-ar","44100","-ac","1",wav],check=True)
        out.append(dict(seg=sg,text=tx,wav=wav,dur=round(dur(wav),3),pause=pa))
    json.dump(out,open("build/ph/phrases.json","w"),ensure_ascii=False,indent=1)
asyncio.run(main())
