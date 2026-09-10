#!/usr/bin/env python3
"""Why does the model score synthetic Takshila 0.94 and real Takshila 0.10?

    python tools/domain_analysis.py --dataset data/dataset_v2

EXP-006 established the failure and rejected level and peak-normalisation as
causes. What remains is "domain gap", which is a label, not a diagnosis. This
script turns it into measurements: WHICH features differ, by HOW MUCH, and in
WHICH part of the clip.

It compares synthetic TTS positives against real INMP441 positives on the exact
features the model consumes, and separates SPEECH frames from the frames around
them - because a real recording carries room tone where a TTS clip carries
digital silence, and those are different problems with different fixes.

Nothing here trains or modifies anything.
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import ARTIFACTS_DIR, DATASET_ROOT  # noqa: E402
from training import features as F  # noqa: E402
from training.dataset import read_manifest  # noqa: E402

OUT = ARTIFACTS_DIR / "domain"


def load_pcm(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")


def log_mel(pcm: np.ndarray) -> np.ndarray:
    """(n_frames, 40) log-mel. More interpretable than MFCC for spectral shape:
    MFCC coefficients are a rotation, so a tilt shows up smeared across them."""
    x = F.pcm16_to_float(pcm)
    n = 1 + max(0, (x.size - F.FRAME_LEN) // F.FRAME_HOP)
    out = np.zeros((n, F.N_MEL))
    for i in range(n):
        fr = x[i * F.FRAME_HOP: i * F.FRAME_HOP + F.FRAME_LEN] * F.HANN
        pad = np.zeros(F.FFT_SIZE)
        pad[:F.FRAME_LEN] = fr
        s = np.fft.rfft(pad, n=F.FFT_SIZE)
        out[i] = np.log(np.maximum(F.MELFB @ (s.real ** 2 + s.imag ** 2), F.LOG_FLOOR))
    return out


def frame_energy_db(pcm: np.ndarray) -> np.ndarray:
    x = F.pcm16_to_float(pcm)
    n = 1 + max(0, (x.size - F.FRAME_LEN) // F.FRAME_HOP)
    e = np.zeros(n)
    for i in range(n):
        fr = x[i * F.FRAME_HOP: i * F.FRAME_HOP + F.FRAME_LEN]
        e[i] = 10 * np.log10((fr ** 2).mean() + 1e-12)
    return e


def speech_mask(energy_db: np.ndarray) -> np.ndarray:
    """Frames belonging to the utterance, by a within-clip relative rule so it
    behaves the same on a loud TTS clip and a quiet real one."""
    if energy_db.size == 0:
        return np.zeros(0, dtype=bool)
    floor = np.percentile(energy_db, 20)
    return energy_db > floor + max(6.0, (energy_db.max() - floor) * 0.35)


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return float((a.mean() - b.mean()) / sp) if sp > 0 else 0.0


def collect(rows, dataset: Path, limit: int, seed: int = 20260910) -> dict:
    rng = np.random.default_rng(seed)
    if len(rows) > limit:
        rows = [rows[i] for i in rng.choice(len(rows), limit, replace=False)]
    mf, lm, sp_mf, sp_lm, en, sp_frac, rms, noise = [], [], [], [], [], [], [], []
    for r in rows:
        pcm = load_pcm(dataset / r["filepath"])
        f = F.clip_features(pcm)                       # (49,13)
        m = log_mel(pcm)[:F.N_FRAMES]
        e = frame_energy_db(pcm)[:F.N_FRAMES]
        k = speech_mask(e)
        mf.append(f)
        lm.append(m)
        en.append(e)
        sp_frac.append(float(k.mean()))
        rms.append(20 * np.log10(np.sqrt((F.pcm16_to_float(pcm) ** 2).mean()) + 1e-12))
        noise.append(float(np.percentile(e, 20)))
        if k.any():
            sp_mf.append(f[k[:len(f)]] if len(k) >= len(f) else f)
            sp_lm.append(m[k[:len(m)]] if len(k) >= len(m) else m)
    return {
        "n": len(rows),
        "mfcc": np.concatenate(mf),                    # (N*49, 13)
        "logmel": np.concatenate(lm),
        "mfcc_speech": np.concatenate(sp_mf) if sp_mf else np.zeros((0, F.N_MFCC)),
        "logmel_speech": np.concatenate(sp_lm) if sp_lm else np.zeros((0, F.N_MEL)),
        "energy": np.concatenate(en),
        "speech_fraction": np.asarray(sp_frac),
        "rms_dbfs": np.asarray(rms),
        "noise_floor_db": np.asarray(noise),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=DATASET_ROOT)
    ap.add_argument("--limit", type=int, default=300)
    args = ap.parse_args()

    rows = []
    for split in ("train", "validation", "test"):
        rows += read_manifest(split, args.dataset)
    syn = [r for r in rows if r["class"] == "positive" and r["synthetic"] == "true"]
    real = [r for r in rows if r["class"] == "positive" and r["synthetic"] == "false"]

    print("=" * 78)
    print("DOMAIN ANALYSIS - synthetic TTS vs real INMP441, keyword 'Takshila'")
    print("=" * 78)
    print(f"  synthetic positives available {len(syn):,}   sampling {min(len(syn), args.limit)}")
    print(f"  real positives available      {len(real):,}   sampling {min(len(real), args.limit)}")

    A = collect(syn, args.dataset, args.limit)
    B = collect(real, args.dataset, args.limit)

    # ---- 1. clip-level acoustics ------------------------------------------
    print(f"\n{'-' * 78}\n1. CLIP-LEVEL ACOUSTICS")
    print(f"  {'measure':<26}{'synthetic':>14}{'real':>14}{'difference':>14}")
    for label, ka, kb in (("RMS dBFS", A["rms_dbfs"], B["rms_dbfs"]),
                          ("noise floor dB", A["noise_floor_db"], B["noise_floor_db"]),
                          ("speech frames fraction", A["speech_fraction"], B["speech_fraction"])):
        print(f"  {label:<26}{np.median(ka):>14.2f}{np.median(kb):>14.2f}"
              f"{np.median(kb) - np.median(ka):>14.2f}")
    a_snr = A["energy"].max() - np.median(A["noise_floor_db"])
    b_snr = B["energy"].max() - np.median(B["noise_floor_db"])
    print(f"  {'peak - noise floor dB':<26}{a_snr:>14.2f}{b_snr:>14.2f}{b_snr - a_snr:>14.2f}")

    # ---- 2. MFCC, all frames vs speech frames -----------------------------
    print(f"\n{'-' * 78}\n2. MFCC PER-COEFFICIENT SHIFT  (real - synthetic, in pooled SD)")
    print("  Cohen's d: |d|>0.8 is a large shift, |d|>2 means the distributions")
    print("  barely overlap. 'all' includes the frames around the word.")
    print(f"\n  {'coef':<7}{'syn mean':>11}{'real mean':>11}{'d (all)':>10}"
          f"{'d (speech only)':>18}")
    d_all, d_sp = [], []
    for c in range(F.N_MFCC):
        da = cohens_d(B["mfcc"][:, c], A["mfcc"][:, c])
        ds = cohens_d(B["mfcc_speech"][:, c], A["mfcc_speech"][:, c])
        d_all.append(da)
        d_sp.append(ds)
        print(f"  c{c:<6}{A['mfcc'][:, c].mean():>11.2f}{B['mfcc'][:, c].mean():>11.2f}"
              f"{da:>10.2f}{ds:>18.2f}")
    print(f"\n  mean |d| all frames    {np.mean(np.abs(d_all)):.2f}")
    print(f"  mean |d| speech only   {np.mean(np.abs(d_sp)):.2f}")
    worst = int(np.argmax(np.abs(d_sp)))
    print(f"  largest speech-frame shift: c{worst} (d = {d_sp[worst]:+.2f})")

    # ---- 3. spectral shape -------------------------------------------------
    print(f"\n{'-' * 78}\n3. SPECTRAL TILT  (log-mel, speech frames only)")
    print("  A constant offset is a level difference. A slope is a channel/response")
    print("  difference, which augmentation could model. Per-band d:")
    edges = np.linspace(F.hz_to_mel(F.MEL_LOW_HZ), F.hz_to_mel(F.MEL_HIGH_HZ), F.N_MEL + 2)
    centres = F.mel_to_hz(edges[1:-1])
    band_d = []
    for m in range(F.N_MEL):
        band_d.append(cohens_d(B["logmel_speech"][:, m], A["logmel_speech"][:, m]))
    band_d = np.asarray(band_d)
    for lo, hi in ((0, 8), (8, 16), (16, 24), (24, 32), (32, 40)):
        print(f"  mel {lo:>2}-{hi - 1:<2} ({centres[lo]:>6.0f}-{centres[hi - 1]:>6.0f} Hz)  "
              f"syn {A['logmel_speech'][:, lo:hi].mean():>7.2f}   "
              f"real {B['logmel_speech'][:, lo:hi].mean():>7.2f}   "
              f"d {band_d[lo:hi].mean():>+6.2f}")
    tilt = band_d[24:].mean() - band_d[:8].mean()
    print(f"\n  low-band d {band_d[:8].mean():+.2f}   high-band d {band_d[24:].mean():+.2f}"
          f"   TILT {tilt:+.2f}")

    # ---- 4. what the model's normalisation does to this --------------------
    print(f"\n{'-' * 78}\n4. AFTER TRAIN NORMALISATION")
    npz = ARTIFACTS_DIR / "model" / "normalisation.npz"
    if npz.is_file():
        nz = np.load(npz)
        mean, std = nz["mean"], nz["std"]
        za = (A["mfcc_speech"] - mean) / std
        zb = (B["mfcc_speech"] - mean) / std
        print("  Training normalisation is per-coefficient, fitted on TRAIN (99.9%")
        print("  synthetic). It centres synthetic speech and leaves real speech off-centre.")
        print(f"  {'coef':<7}{'syn z-mean':>13}{'real z-mean':>13}{'offset':>10}")
        offs = []
        for c in range(F.N_MFCC):
            o = zb[:, c].mean() - za[:, c].mean()
            offs.append(o)
            print(f"  c{c:<6}{za[:, c].mean():>13.2f}{zb[:, c].mean():>13.2f}{o:>10.2f}")
        print(f"\n  RMS displacement of real speech in normalised space: "
              f"{np.sqrt(np.mean(np.square(offs))):.2f} SD")
        print("  A model whose inputs are z-scored sees real speech as an input")
        print("  distribution it was never trained on, by this many standard deviations.")
    else:
        print("  normalisation.npz not found - skipped")
        offs = []

    # ---- 5. duration -------------------------------------------------------
    print(f"\n{'-' * 78}\n5. KEYWORD DURATION")
    for label, rr in (("synthetic", syn), ("real", real)):
        d = [float(r["keyword_offset_ms"]) - float(r["keyword_onset_ms"])
             for r in rr if r.get("keyword_onset_ms") and r.get("keyword_offset_ms")]
        if d:
            print(f"  {label:<11} n={len(d):<6} median {np.median(d):>6.0f} ms   "
                  f"p10 {np.percentile(d, 10):>5.0f}   p90 {np.percentile(d, 90):>5.0f}")

    rec = {
        "analysed_utc": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ",
                                                    __import__("time").gmtime()),
        "n_synthetic": A["n"], "n_real": B["n"],
        "clip_acoustics": {
            "rms_dbfs": {"syn": float(np.median(A["rms_dbfs"])),
                         "real": float(np.median(B["rms_dbfs"]))},
            "noise_floor_db": {"syn": float(np.median(A["noise_floor_db"])),
                               "real": float(np.median(B["noise_floor_db"]))},
            "speech_fraction": {"syn": float(np.median(A["speech_fraction"])),
                                "real": float(np.median(B["speech_fraction"]))},
        },
        "mfcc_cohens_d_all": [float(v) for v in d_all],
        "mfcc_cohens_d_speech": [float(v) for v in d_sp],
        "mean_abs_d_all": float(np.mean(np.abs(d_all))),
        "mean_abs_d_speech": float(np.mean(np.abs(d_sp))),
        "logmel_band_d": [float(v) for v in band_d],
        "spectral_tilt_d": float(tilt),
        "normalised_offset_sd": [float(v) for v in offs],
        "normalised_rms_displacement_sd": float(np.sqrt(np.mean(np.square(offs))))
        if offs else None,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "domain_analysis.json").write_text(json.dumps(rec, indent=2) + "\n",
                                              encoding="utf-8")
    print(f"\nwrote {OUT / 'domain_analysis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
