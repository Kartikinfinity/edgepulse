#!/usr/bin/env python3
"""Pull a small, representative listening set out of the built dataset.

    python tools/dataset_examples.py
    python tools/dataset_examples.py --per-class 6 --out data/dataset_examples

Nobody should train on a dataset they have not listened to. This copies a
stratified sample - every class, both real and synthetic, a spread of SNR - into
one flat directory with self-describing filenames, plus an index.csv.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dataset_factory.audio import rng_for            # noqa: E402
from tools.dataset_factory.config import OUT_DIR           # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=OUT_DIR)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--per-class", type=int, default=5)
    args = ap.parse_args()

    man = args.dataset / "manifests" / "all.csv"
    if not man.is_file():
        sys.exit(f"ERROR: no manifest at {man} — build the dataset first")
    rows = list(csv.DictReader(man.open(encoding="utf-8")))
    out = args.out or (args.dataset.parent / "dataset_examples")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    # stratify by (class, synthetic) so real audio is always represented
    groups: dict[tuple, list] = defaultdict(list)
    for r in rows:
        groups[(r["class"], r["synthetic"])].append(r)

    picked = []
    for key in sorted(groups):
        pool = sorted(groups[key], key=lambda r: r["clip_id"])
        rng = rng_for("examples", *key)
        n = min(args.per_class, len(pool))
        idx = rng.choice(len(pool), n, replace=False) if len(pool) > n else range(len(pool))
        for i in idx:
            picked.append(pool[int(i)])

    with (out / "index.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["example_file", "class", "sub_label", "split", "synthetic",
                    "microphone", "source_corpus", "text", "snr_db", "rms_dbfs",
                    "augmentation", "original_clip_id"])
        for r in picked:
            real = "real" if r["synthetic"] == "false" else "tts"
            name = (f"{r['class']}__{real}__{r['split']}__{r['clip_id']}.wav"
                    .replace("/", "-"))
            src = args.dataset / r["filepath"]
            if not src.is_file():
                continue
            shutil.copy2(src, out / name)
            w.writerow([name, r["class"], r["sub_label"], r["split"], r["synthetic"],
                        r["microphone"], r["source_corpus"], r["text"],
                        r["snr_db"], r["rms_dbfs"], r["augmentation"], r["clip_id"]])

    n = len(list(out.glob("*.wav")))
    print(f"wrote {n} example clips to {out}")
    print(f"index: {out/'index.csv'}")
    print("\nListen to these before training. In particular check that:")
    print("  - positive/real  clips actually contain the keyword, whole and in-window")
    print("  - positive/tts   clips are intelligible as 'Takshila'")
    print("  - hard_negative/partial clips contain only PART of the keyword")
    print("  - near_homophone clips are the confusable, not the keyword")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
