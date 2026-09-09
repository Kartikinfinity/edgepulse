#!/usr/bin/env python3
"""Band-limited energy analysis: where does the spoken word sit inside a clip?

Dataset-agnostic. Point it at any directory of WAV files.

    python tools/audio_probe_bands.py <directory> [--band 300 3400] [--bins 20]
    python tools/audio_probe_bands.py recordings/keyword --sample 200

Two questions it answers, both of which matter when designing a KWS dataset:

  1. WHERE in the clip is the speech?  Speech-band energy is binned across the
     clip and the peak bin located. A tightly centred distribution means the
     recordings are centred, which is exactly the condition that makes a
     clip-trained model fail on sliding windows (see DECISIONS.md D-005).
     Deliberate positional spread is what you want.

  2. HOW separable is speech from the background by energy alone? The fraction
     of total energy inside the speech band is reported per directory. If two
     classes have similar fractions, an energy-only VAD cannot separate them and
     must not be used as a hard gate.

Run this on new recordings while designing the dataset, not after training.
"""

from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal


def read_mono(path: Path):
    """Return (samples_float32_in_[-1,1), sample_rate)."""
    with wave.open(str(path), "rb") as w:
        rate, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, rate


def band_energy_profile(x: np.ndarray, rate: int, lo: float, hi: float, bins: int):
    """Return (per-bin band energy, band energy fraction of total)."""
    nyq = rate / 2.0
    lo_n, hi_n = max(1e-6, lo / nyq), min(0.999, hi / nyq)
    sos = signal.butter(4, [lo_n, hi_n], btype="band", output="sos")
    band = signal.sosfilt(sos, x)

    total_e = float(np.sum(x * x))
    band_e = float(np.sum(band * band))
    frac = band_e / total_e if total_e > 0 else 0.0

    edges = np.linspace(0, len(band), bins + 1).astype(int)
    profile = np.array([float(np.sum(band[edges[i]:edges[i + 1]] ** 2)) for i in range(bins)])
    return profile, frac


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("directory", type=Path)
    ap.add_argument("--band", type=float, nargs=2, default=(300.0, 3400.0),
                    metavar=("LO_HZ", "HI_HZ"), help="speech band, default 300 3400")
    ap.add_argument("--bins", type=int, default=20, help="time bins per clip, default 20")
    ap.add_argument("--sample", type=int, default=0, help="files to probe (0 = all)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    root: Path = args.directory
    if not root.is_dir():
        sys.exit(f"ERROR: not a directory: {root}")
    files = sorted(root.rglob("*.wav"))
    if not files:
        sys.exit(f"ERROR: no .wav files found under {root}")
    if args.sample and args.sample < len(files):
        import random
        files = random.Random(args.seed).sample(files, args.sample)

    lo, hi = args.band
    print("=" * 70)
    print(f"BAND-LIMITED PROFILE  {root}")
    print(f"band {lo:.0f}-{hi:.0f} Hz · {args.bins} bins/clip · {len(files):,} files")
    print("=" * 70)

    peak_bins, fracs, spans = [], [], []
    for path in files:
        try:
            x, rate = read_mono(path)
        except Exception:
            continue
        if x.size < 64:
            continue
        profile, frac = band_energy_profile(x, rate, lo, hi, args.bins)
        fracs.append(frac)
        if profile.sum() <= 0:
            continue
        peak_bins.append(int(np.argmax(profile)))
        # "active" = bins holding at least 10% of the peak bin's energy
        active = int(np.sum(profile >= 0.10 * profile.max()))
        spans.append(active * (len(x) / rate) / args.bins)

    if not fracs:
        sys.exit("ERROR: no readable audio")

    f = np.array(fracs)
    print(f"\n-- speech-band energy fraction --")
    print(f"  mean {f.mean():.3f}   min {f.min():.3f}   max {f.max():.3f}   n={len(f)}")
    print("  Compare across classes: similar values mean an energy-only VAD")
    print("  cannot separate them and must not gate the detector.")

    if peak_bins:
        pb = np.array(peak_bins)
        sp = np.array(spans)
        print(f"\n-- position of peak energy within the clip --")
        print(f"  peak bin: mean {pb.mean():.1f} / {args.bins}   std {pb.std():.1f} bins")
        print(f"  active span: mean {sp.mean() * 1000:.0f} ms")
        print("\n  histogram of peak bin (clip start -> end):")
        hist = np.bincount(pb, minlength=args.bins)
        width = max(1, hist.max())
        for i, c in enumerate(hist):
            bar = "#" * int(40 * c / width)
            print(f"   bin {i:>2} |{bar:<40}| {c}")
        print("\n  A tight central peak means centred recordings, which produce a")
        print("  model that fails on sliding windows. Spread is what you want.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
