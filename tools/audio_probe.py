#!/usr/bin/env python3
"""Audit the format and level statistics of a directory of WAV files.

Dataset-agnostic: point it at any directory and it recurses. It makes no
assumption about split/class layout, filenames, or a manifest schema.

    python tools/audio_probe.py <directory> [--sample N] [--seed S]
    python tools/audio_probe.py recordings/session_01
    python tools/audio_probe.py recordings --sample 0        # 0 = every file

Reports, per the pool it scanned:
  * format uniformity  - channels, rate, sample width, frame count
  * duration statistics
  * level statistics    - RMS, peak, and full-scale (clipped) sample counts

Use this on new recordings BEFORE building a dataset from them. Nothing here is
specific to any keyword or corpus.
"""

from __future__ import annotations

import argparse
import collections
import random
import sys
import wave
from pathlib import Path

import numpy as np


def read_wav(path: Path):
    """Return (channels, rate, sampwidth, nframes, samples_int16_or_None)."""
    with wave.open(str(path), "rb") as w:
        ch, rate, sw, n = w.getnchannels(), w.getframerate(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    samples = np.frombuffer(raw, dtype="<i2") if sw == 2 else None
    return ch, rate, sw, n, samples


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("directory", type=Path, help="directory to scan recursively for .wav")
    ap.add_argument("--sample", type=int, default=1500,
                    help="how many files to probe (0 = all). Default 1500.")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    root: Path = args.directory
    if not root.is_dir():
        sys.exit(f"ERROR: not a directory: {root}")

    files = sorted(root.rglob("*.wav"))
    if not files:
        sys.exit(f"ERROR: no .wav files found under {root}")

    pool = files
    if args.sample and args.sample < len(files):
        pool = random.Random(args.seed).sample(files, args.sample)

    print("=" * 70)
    print(f"AUDIO PROBE  {root}")
    print("=" * 70)
    print(f"wav files found : {len(files):,}")
    print(f"files probed    : {len(pool):,}"
          + ("  (all)" if len(pool) == len(files) else f"  (random, seed={args.seed})"))
    print()

    formats = collections.Counter()
    frame_counts = collections.Counter()
    rms_vals, peak_vals = [], []
    clipped_files = 0
    unreadable = []

    for path in pool:
        try:
            ch, rate, sw, n, samples = read_wav(path)
        except Exception as exc:
            unreadable.append((path, exc))
            continue
        formats[(ch, rate, sw)] += 1
        frame_counts[n] += 1
        if samples is not None and samples.size:
            x = samples.astype(np.float32) / 32768.0
            rms_vals.append(float(np.sqrt(np.mean(x * x))))
            peak = float(np.max(np.abs(x)))
            peak_vals.append(peak)
            if np.any(np.abs(samples) >= 32767):
                clipped_files += 1

    print("-- format (channels, rate_hz, sample_width_bytes) --")
    for fmt, count in formats.most_common():
        pct = 100.0 * count / max(1, len(pool) - len(unreadable))
        print(f"  {fmt}  {count:>7,}  {pct:6.2f} %")
    if len(formats) == 1:
        print("  => uniform")
    else:
        print("  => MIXED FORMATS - resolve before building a dataset")
    print()

    print("-- frame count (clip length in samples) --")
    for n, count in frame_counts.most_common(8):
        rate = next(iter(formats))[1] if formats else 16000
        print(f"  {n:>8,} frames ({n / rate:6.3f} s)  {count:>7,} files")
    if len(frame_counts) > 8:
        print(f"  ... and {len(frame_counts) - 8} other lengths")
    print(f"  => {'uniform' if len(frame_counts) == 1 else 'VARIABLE length'}")
    print()

    if rms_vals:
        r = np.array(rms_vals)
        p = np.array(peak_vals)
        print("-- levels (normalised to full scale = 1.0) --")
        print(f"  RMS   min {r.min():.4f}  mean {r.mean():.4f}  max {r.max():.4f}")
        print(f"  peak  min {p.min():.4f}  mean {p.mean():.4f}  max {p.max():.4f}")
        print(f"  files containing a full-scale sample (clipping): {clipped_files} "
              f"({100.0 * clipped_files / len(rms_vals):.1f} %)")
        print()

    if unreadable:
        print(f"-- UNREADABLE: {len(unreadable)} file(s) --")
        for path, exc in unreadable[:5]:
            print(f"  {path.name}: {exc}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
