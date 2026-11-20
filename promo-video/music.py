# Synthesizes a simple upbeat background track (15s) + transition whooshes -> build/music.wav
import numpy as np, wave
SR=44100; DUR=15.0; N=int(SR*DUR); t=np.arange(N)/SR
out=np.zeros(N)
bpm=112; beat=60/bpm
def note(f): return 440*2**((f-69)/12)
chords=[[60,64,67],[67,71,74],[69,72,76],[65,69,72]]  # C G Am F
bar=beat*4
for i in range(int(DUR/bar)+1):
    ch=chords[i%4]; s=int(i*bar*SR); e=min(N,int((i+1)*bar*SR))
    if s>=N: break
    tt=t[s:e]-i*bar
    env=np.minimum(1,tt/0.05)*np.exp(-tt*0.35)
    for m in ch:
        f=note(m-12)
        out[s:e]+=0.05*env*(np.sin(2*np.pi*f*tt)+0.3*np.sin(2*np.pi*2*f*tt))
    # bass on each beat
    for b in range(4):
        bs=s+int(b*beat*SR); be=min(N,bs+int(beat*SR))
        if bs>=N: break
        tb=t[bs:be]-t[bs]; f=note(ch[0]-24)
        out[bs:be]+=0.12*np.exp(-tb*6)*np.sin(2*np.pi*f*tb)
# drums
rng=np.random.default_rng(1)
k=0
while k*beat<DUR:
    s=int(k*beat*SR); L=min(N-s,int(0.25*SR)); tb=np.arange(L)/SR
    f=120*np.exp(-tb*25)+45; ph=2*np.pi*np.cumsum(f)/SR
    out[s:s+L]+=0.35*np.exp(-tb*14)*np.sin(ph)
    hs=int((k+0.5)*beat*SR)
    if hs<N:
        L2=min(N-hs,int(0.05*SR)); out[hs:hs+L2]+=0.04*rng.standard_normal(L2)*np.exp(-np.arange(L2)/SR*80)
    k+=1
# whooshes at scene changes
for c in [3.05,6.85,10.75]:
    s=int((c-0.35)*SR); L=int(0.5*SR); tb=np.arange(L)/SR
    n=rng.standard_normal(L); n=np.convolve(n,np.ones(8)/8,'same')
    env=np.sin(np.pi*tb/0.5)**2
    out[s:s+L]+=0.18*n*env
# fade in/out
out*=np.minimum(1,t/0.3)*np.minimum(1,(DUR-t)/0.8)
out/=np.max(np.abs(out))*1.1
with wave.open('build/music.wav','wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out*32767).astype(np.int16).tobytes())
