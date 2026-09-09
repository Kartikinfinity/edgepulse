import wave, os, csv, collections, numpy as np
from scipy import signal
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import DATASET_FULL

if not DATASET_FULL.is_dir():
    sys.exit(
        f"ERROR: dataset not found at {DATASET_FULL}\n"
        "  The dataset is not stored in Git. See DATASET_SETUP.md to obtain it,\n"
        "  or set SIH_DATASET_ROOT in .env if it lives elsewhere on this machine."
    )

ROOT = str(DATASET_FULL)
def rd(p):
    with wave.open(p,'rb') as w:
        return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768.0
rows=[]
for split in ("train","validation","test"):
    with open(os.path.join(ROOT,"manifests",split+".csv"),newline='',encoding='utf-8') as f:
        rows+=list(csv.DictReader(f))
SR=16000
def bandenv(x, lo, hi, nb=20):
    f,t,S=signal.spectrogram(x,SR,nperseg=256,noverlap=128,mode='magnitude')
    m=(f>=lo)&(f<hi)
    e=S[m].sum(0)
    # resample to nb bins
    idx=np.linspace(0,len(e),nb+1).astype(int)
    return np.array([e[idx[i]:idx[i+1]].mean() if idx[i+1]>idx[i] else 0 for i in range(nb)])

for lab,band in (("positive",(300,3400)),("positive",(3400,7800))):
    sel=[r for r in rows if r['label']==lab and r['augmentation']=='none']
    E=[]
    for r in sel:
        x=rd(os.path.join(ROOT,r['filepath'].replace('/',os.sep)))
        b=bandenv(x,*band); E.append(b/(b.max()+1e-12))
    E=np.array(E); m=E.mean(0)
    print(f"\n== {lab} unaugmented, band {band[0]}-{band[1]} Hz, n={len(sel)} ==")
    for i,v in enumerate(m): print(f"  {i*50:4d}-{(i+1)*50:4d} ms  {v:.3f} "+"#"*int(v*46))
    pk=E.argmax(1)
    print("  peak-bin histogram:",dict(sorted(collections.Counter(pk.tolist()).items())))
    print("  peak bin: mean=%.1f median=%.1f std=%.1f"%(pk.mean(),np.median(pk),pk.std()))
    # extent above 40% of peak
    fs=[];ls=[]
    for e in E:
        idx=np.where(e>0.40)[0]; fs.append(idx[0]); ls.append(idx[-1])
    print("  onset bin  mean=%.1f median=%.1f  | offset bin mean=%.1f median=%.1f"%(np.mean(fs),np.median(fs),np.mean(ls),np.median(ls)))
    print("  => active span mean %.0f ms  (lead %.0f ms, trail %.0f ms)"%((np.mean(ls)-np.mean(fs)+1)*50, np.mean(fs)*50, (19-np.mean(ls))*50))

# compare speech-band occupancy: positive vs background vs negative
print("\n== speech-band (300-3400 Hz) fraction of total energy ==")
for lab in ("positive","negative","background"):
    sel=[r for r in rows if r['label']==lab and r['augmentation']=='none'][:300]
    fr=[]
    for r in sel:
        x=rd(os.path.join(ROOT,r['filepath'].replace('/',os.sep)))
        f,P=signal.welch(x,SR,nperseg=512)
        tot=P.sum(); fr.append(P[(f>=300)&(f<3400)].sum()/(tot+1e-20))
    print(f"  {lab:11s} n={len(sel):4d}  mean={np.mean(fr):.3f}  median={np.median(fr):.3f}")
