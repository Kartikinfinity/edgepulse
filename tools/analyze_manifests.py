import csv, collections, os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import DATASET_ROOT

if not DATASET_ROOT.is_dir():
    sys.exit(
        f"ERROR: dataset not found at {DATASET_ROOT}\n"
        "  The dataset is not stored in Git. See DATASET_SETUP.md to obtain it,\n"
        "  or set SIH_DATASET_ROOT in .env if it lives elsewhere on this machine."
    )

ROOT = str(DATASET_ROOT)

def load(ds):
    rows=[]
    for split in ("train","validation","test"):
        p=os.path.join(ROOT,ds,"manifests",split+".csv")
        with open(p,newline='',encoding='utf-8') as f:
            for r in csv.DictReader(f):
                rows.append(r)
    return rows

for ds in ("dataset_full","dataset_balanced"):
    rows=load(ds)
    print("="*70); print(ds, "rows:",len(rows))
    # class x split
    cs=collections.Counter((r['split'],r['label']) for r in rows)
    print("\n-- split x label --")
    for split in ("train","validation","test"):
        tot=sum(v for (s,l),v in cs.items() if s==split)
        print(f"  {split:11s} total={tot:6d}  " + "  ".join(f"{l}={cs[(split,l)]}" for l in ("positive","negative","background")))

    # UNIQUE source recordings
    print("\n-- unique source_id per label --")
    for lab in ("positive","negative","background"):
        ids={r['source_id'] for r in rows if r['label']==lab}
        srcs={r['original_source'] for r in rows if r['label']==lab}
        n=sum(1 for r in rows if r['label']==lab)
        print(f"  {lab:11s} clips={n:6d}  unique source_id={len(ids):6d}  unique original_source={len(srcs):6d}")

    # LEAKAGE: source_id spanning splits
    print("\n-- LEAKAGE CHECK: source_id appearing in >1 split --")
    bysid=collections.defaultdict(set)
    for r in rows: bysid[r['source_id']].add(r['split'])
    span=[k for k,v in bysid.items() if len(v)>1]
    print(f"  source_id spanning multiple splits: {len(span)} / {len(bysid)}")
    if span[:5]: print("   examples:", span[:5])

    print("\n-- LEAKAGE CHECK: original_source (raw recording) appearing in >1 split --")
    byos=collections.defaultdict(set)
    for r in rows: byos[r['original_source']].add(r['split'])
    span2=[k for k,v in byos.items() if len(v)>1]
    print(f"  original_source spanning multiple splits: {len(span2)} / {len(byos)}")
    for k in span2[:8]:
        print(f"    {sorted(byos[k])}  {k[:90]}")

    # positives: unique sources per split
    print("\n-- POSITIVES: unique original_source per split --")
    for split in ("train","validation","test"):
        s={r['original_source'] for r in rows if r['label']=='positive' and r['split']==split}
        sid={r['source_id'] for r in rows if r['label']=='positive' and r['split']==split}
        n=sum(1 for r in rows if r['label']=='positive' and r['split']==split)
        print(f"  {split:11s} clips={n:5d}  unique source_id={len(sid):4d}  unique raw file={len(s):4d}")

    # positives: environment / augmentation
    print("\n-- POSITIVES: environment --")
    for k,v in collections.Counter(r['environment'] for r in rows if r['label']=='positive').most_common():
        print(f"    {v:6d}  {k!r}")
    print("-- POSITIVES: speaker --")
    for k,v in collections.Counter(r['speaker'] for r in rows if r['label']=='positive').most_common():
        print(f"    {v:6d}  {k!r}")
    print("-- POSITIVES: source_dataset --")
    for k,v in collections.Counter(r['source_dataset'] for r in rows if r['label']=='positive').most_common():
        print(f"    {v:6d}  {k!r}")
    print("-- NEGATIVES: source_dataset --")
    for k,v in collections.Counter(r['source_dataset'] for r in rows if r['label']=='negative').most_common():
        print(f"    {v:6d}  {k!r}")
    print("-- BACKGROUND: source_dataset --")
    for k,v in collections.Counter(r['source_dataset'] for r in rows if r['label']=='background').most_common():
        print(f"    {v:6d}  {k!r}")
    print()
