import wave, os, csv, collections, numpy as np, random
ROOT = r"E:\sih2026\data\solvani_kws_release\dataset_full"

def rd(p):
    with wave.open(p,'rb') as w:
        return w.getnchannels(), w.getframerate(), w.getsampwidth(), w.getnframes(), np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')

rows=[]
for split in ("train","validation","test"):
    with open(os.path.join(ROOT,"manifests",split+".csv"),newline='',encoding='utf-8') as f:
        rows+=list(csv.DictReader(f))
print("manifest rows:",len(rows))
# verify files exist
missing=[r for r in rows if not os.path.exists(os.path.join(ROOT,r['filepath'].replace('/',os.sep)))]
print("missing files:",len(missing))
# count actual wavs on disk
onchdisk=0
for dp,dn,fn in os.walk(ROOT):
    onchdisk+=sum(1 for x in fn if x.lower().endswith('.wav'))
print("wavs on disk:",onchdisk)

# format audit over a large random sample
random.seed(0)
samp=random.sample(rows,1500)
fmt=collections.Counter(); dur=collections.Counter()
for r in samp:
    ch,sr,sw,nf,_=rd(os.path.join(ROOT,r['filepath'].replace('/',os.sep)))
    fmt[(ch,sr,sw)]+=1; dur[nf]+=1
print("\nformat (ch,rate,samplewidth):",dict(fmt))
print("frame counts:",dict(dur))

# ---- positive envelope position: where does energy sit inside the 1.0 s window? ----
pos=[r for r in rows if r['label']=='positive' and r['augmentation']=='none']
print("\nunaugmented positives:",len(pos))
ENV=[]; peaks=[]; clip=0; rmsall=[]
for r in pos:
    _,_,_,_,x=rd(os.path.join(ROOT,r['filepath'].replace('/',os.sep)))
    x=x.astype(np.float32)/32768.0
    if np.max(np.abs(x))>=0.999: clip+=1
    rmsall.append(float(np.sqrt(np.mean(x**2))))
    # 20 bins of energy
    n=len(x); b=np.array([np.sqrt(np.mean(x[i*n//20:(i+1)*n//20]**2)) for i in range(20)])
    ENV.append(b/ (b.max()+1e-9))
    peaks.append(int(np.argmax(b)))
ENV=np.array(ENV)
print("clipped positives:",clip," rms mean=%.4f min=%.4f max=%.4f"%(np.mean(rmsall),np.min(rmsall),np.max(rmsall)))
print("\nmean normalised energy envelope across 20 bins (0=start,19=end of the 1.0 s clip):")
m=ENV.mean(0)
for i,v in enumerate(m):
    print(f"  bin {i:2d} [{i*50:4d}-{(i+1)*50:4d} ms]  {v:.3f}  " + "#"*int(v*50))
print("\npeak-energy bin histogram:", dict(sorted(collections.Counter(peaks).items())))

# active-speech extent per clip (bins above 25% of that clip's peak)
first=[];last=[]
for e in ENV:
    idx=np.where(e>0.25)[0]
    first.append(idx[0]); last.append(idx[-1])
print("\nspeech onset bin: mean=%.1f median=%.1f min=%d max=%d"%(np.mean(first),np.median(first),min(first),max(first)))
print("speech offset bin: mean=%.1f median=%.1f min=%d max=%d"%(np.mean(last),np.median(last),min(last),max(last)))
print("=> leading silence mean %.0f ms, trailing silence mean %.0f ms"%(np.mean(first)*50,(19-np.mean(last))*50))
