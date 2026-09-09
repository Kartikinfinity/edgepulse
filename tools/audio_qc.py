#!/usr/bin/env python3
"""Automated QC for captured audio — the STEP 4 exit-criteria checker.

    python tools/audio_qc.py <file-or-directory> [--plot]

Measures, per file:
  sample rate · channels · bit depth · duration accuracy · RMS · peak ·
  clipping · DC offset · silence percentage · dropout/zero-run count ·
  malformed samples · bit alignment evidence · frequency sanity (spectral
  centroid, LF/speech/HF energy split) · estimated SNR

Prints a human-readable report and exits non-zero if any REQUIRED check fails,
so it can gate the pilot. With --plot it also writes waveform + spectrum PNGs
(needs matplotlib; skipped cleanly if absent).
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

EXPECT_RATE = 16000
EXPECT_CH = 1
EXPECT_WIDTH = 2          # bytes -> PCM16

# Thresholds (DEMO_DATASET_SPEC.md 16 / RESEARCH_DATASET_ROADMAP.md 29)
RMS_MIN_DBFS = -40.0
RMS_MAX_DBFS = -6.0
CLIP_MAX_PCT = 0.1
DC_MAX_FS = 0.002
ZERO_RUN_MS = 20.0        # a gap longer than this mid-signal implies DMA loss
DURATION_TOL_PCT = 1.0

OK, WARN, BAD = "[ ok ]", "[warn]", "[FAIL]"


def db(x: float) -> float:
    return 20.0 * np.log10(max(x, 1e-12))


def load(path: Path):
    with wave.open(str(path), "rb") as w:
        p = {"rate": w.getframerate(), "ch": w.getnchannels(),
             "width": w.getsampwidth(), "frames": w.getnframes()}
        raw = w.readframes(p["frames"])
    if p["width"] != 2:
        return None, p, None
    x = np.frombuffer(raw, dtype="<i2")
    if p["ch"] > 1:
        x = x.reshape(-1, p["ch"])[:, 0]
    return x, p, raw


def longest_zero_run(x: np.ndarray) -> int:
    """Longest run of exact zeros — the signature of a dropped DMA buffer."""
    if x.size == 0:
        return 0
    z = (x == 0).astype(np.int8)
    if not z.any():
        return 0
    d = np.diff(np.concatenate(([0], z, [0])))
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return int((ends - starts).max()) if starts.size else 0


def band_energies(x: np.ndarray, rate: int):
    """Fractional energy below 100 Hz, in 300-3400 Hz, and above 4 kHz."""
    if x.size < 512:
        return 0.0, 0.0, 0.0, 0.0
    n = 1 << int(np.floor(np.log2(min(x.size, 65536))))
    seg = x[:n].astype(np.float64) / 32768.0
    seg = seg - seg.mean()
    spec = np.abs(np.fft.rfft(seg * np.hanning(n))) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / rate)
    total = spec.sum()
    if total <= 0:
        return 0.0, 0.0, 0.0, 0.0
    lf = spec[freqs < 100].sum() / total
    sp = spec[(freqs >= 300) & (freqs <= 3400)].sum() / total
    hf = spec[freqs >= 4000].sum() / total
    centroid = float((freqs * spec).sum() / total)
    return float(lf), float(sp), float(hf), centroid


def estimate_snr(x: np.ndarray) -> float:
    """Crude but honest: loudest decile vs quietest decile, in 20 ms frames."""
    if x.size < 3200:
        return float("nan")
    f = 320
    n = x.size // f
    e = (x[:n * f].astype(np.float64).reshape(n, f) ** 2).mean(axis=1)
    e = np.sort(e)
    lo = e[: max(1, n // 10)].mean()
    hi = e[-max(1, n // 10):].mean()
    if lo <= 0 or hi <= 0:
        return float("nan")
    return float(10.0 * np.log10(hi / lo))


def analyse(path: Path) -> dict:
    x, p, raw = load(path)
    r = {"file": path.name, "path": str(path), **p, "fails": [], "warns": []}
    if x is None:
        r["fails"].append(f"sample width {p['width']}B, expected 2B (PCM16)")
        return r

    xf = x.astype(np.float64) / 32768.0
    n = x.size

    r["duration_s"] = n / p["rate"] if p["rate"] else 0.0
    r["rms"] = float(np.sqrt((xf ** 2).mean())) if n else 0.0
    r["rms_dbfs"] = db(r["rms"])
    r["peak"] = float(np.abs(xf).max()) if n else 0.0
    r["peak_dbfs"] = db(r["peak"])
    r["dc_offset"] = float(xf.mean()) if n else 0.0
    r["clipped"] = int((np.abs(x) >= 32767).sum())
    r["clipped_pct"] = 100.0 * r["clipped"] / n if n else 0.0
    r["zero_pct"] = 100.0 * int((x == 0).sum()) / n if n else 0.0
    run = longest_zero_run(x)
    r["longest_zero_run"] = run
    r["longest_zero_run_ms"] = 1000.0 * run / p["rate"] if p["rate"] else 0.0
    r["snr_db"] = estimate_snr(x)

    # silence % over 20 ms frames at -50 dBFS
    if n >= 320:
        f = 320
        m = n // f
        fr = np.sqrt((xf[:m * f].reshape(m, f) ** 2).mean(axis=1))
        r["silence_pct"] = 100.0 * float((fr < 10 ** (-50 / 20)).sum()) / m
    else:
        r["silence_pct"] = 0.0

    lf, sp, hf, cen = band_energies(x, p["rate"])
    r.update(lf_frac=lf, speech_frac=sp, hf_frac=hf, centroid_hz=cen)

    # Bit-alignment evidence: if PCM16 came from a 24-in-32 slot shifted by 16,
    # the low bits are populated normally. An all-even or heavily quantised LSB
    # distribution suggests an over-shift.
    r["distinct_lsb"] = int(len(np.unique(x & 0xFF))) if n else 0
    r["all_even"] = bool(n and not (x & 1).any())

    # ---- REQUIRED checks -------------------------------------------------
    if p["rate"] != EXPECT_RATE:
        r["fails"].append(f"sample rate {p['rate']} != {EXPECT_RATE}")
    if p["ch"] != EXPECT_CH:
        r["fails"].append(f"channels {p['ch']} != {EXPECT_CH}")
    if n == 0:
        r["fails"].append("no audio frames")
    if r["clipped_pct"] > CLIP_MAX_PCT:
        r["fails"].append(f"clipping {r['clipped_pct']:.3f}% > {CLIP_MAX_PCT}%")
    if r["longest_zero_run_ms"] > ZERO_RUN_MS and r["silence_pct"] < 95:
        r["fails"].append(f"zero run {r['longest_zero_run_ms']:.1f} ms > {ZERO_RUN_MS} ms "
                          "(possible DMA dropout)")
    if abs(r["dc_offset"]) > DC_MAX_FS:
        r["fails"].append(f"DC offset {r['dc_offset']:+.5f} FS > {DC_MAX_FS}")

    # ---- advisory --------------------------------------------------------
    if r["rms_dbfs"] < RMS_MIN_DBFS:
        r["warns"].append(f"quiet: RMS {r['rms_dbfs']:.1f} dBFS < {RMS_MIN_DBFS}")
    if r["rms_dbfs"] > RMS_MAX_DBFS:
        r["warns"].append(f"hot: RMS {r['rms_dbfs']:.1f} dBFS > {RMS_MAX_DBFS}")
    if r["all_even"]:
        r["warns"].append("every sample even — possible over-shift / lost LSB")
    if r["lf_frac"] > 0.80 and r["speech_frac"] < 0.05:
        r["warns"].append(f"{100*r['lf_frac']:.0f}% of energy < 100 Hz — mostly rumble")

    # duration vs sidecar metadata, if present
    side = path.with_suffix(".json")
    if side.is_file():
        try:
            meta = json.loads(side.read_text(encoding="utf-8"))
            exp = meta.get("audio", {}).get("samples_expected")
            if exp:
                drift = 100.0 * (n - exp) / exp
                r["duration_drift_pct"] = drift
                if abs(drift) > DURATION_TOL_PCT:
                    r["fails"].append(f"length {n} vs expected {exp} ({drift:+.2f}%)")
            cs = meta.get("capture_stats", {})
            if cs.get("lost_blocks"):
                r["fails"].append(f"{cs['lost_blocks']} block(s) lost in transport")
            if cs.get("overrun_blocks"):
                r["fails"].append(f"{cs['overrun_blocks']} DMA overrun block(s)")
            if cs.get("device_measured_rate_hz"):
                r["device_measured_rate_hz"] = cs["device_measured_rate_hz"]
        except Exception as exc:
            r["warns"].append(f"metadata unreadable: {exc}")
    return r


def plot(path: Path, out_dir: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  (matplotlib absent — skipping plots)")
        return
    x, p, _ = load(path)
    if x is None or x.size == 0:
        return
    xf = x.astype(np.float64) / 32768.0
    t = np.arange(x.size) / p["rate"]
    fig, ax = plt.subplots(2, 1, figsize=(11, 6))
    ax[0].plot(t, xf, lw=0.4)
    ax[0].set(title=f"{path.name} — waveform", xlabel="s", ylabel="FS", ylim=(-1, 1))
    ax[0].grid(alpha=.3)
    ax[1].specgram(xf, NFFT=512, Fs=p["rate"], noverlap=384, cmap="magma")
    ax[1].set(title="spectrogram", xlabel="s", ylabel="Hz")
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{path.stem}_qc.png", dpi=110)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", type=Path)
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    if args.target.is_dir():
        files = sorted(args.target.rglob("*.wav"))
    elif args.target.is_file():
        files = [args.target]
    else:
        sys.exit(f"ERROR: not found: {args.target}")
    if not files:
        sys.exit(f"ERROR: no .wav under {args.target}")

    print("=" * 78)
    print("AUDIO QC REPORT")
    print("=" * 78)
    print(f"target : {args.target}")
    print(f"files  : {len(files)}\n")

    results, n_fail, n_warn = [], 0, 0
    for f in files:
        r = analyse(f)
        results.append(r)
        status = BAD if r["fails"] else (WARN if r["warns"] else OK)
        print(f"{status} {r['file']}")
        if "duration_s" in r:
            print(f"        {r['rate']} Hz  {r['ch']}ch  {r['width']*8}-bit  "
                  f"{r['frames']} frames  {r['duration_s']:.3f} s")
            print(f"        RMS {r['rms_dbfs']:7.1f} dBFS   peak {r['peak_dbfs']:7.1f} dBFS   "
                  f"DC {r['dc_offset']:+.5f}")
            print(f"        clip {r['clipped']} ({r['clipped_pct']:.3f}%)   "
                  f"zeros {r['zero_pct']:.1f}%   longest-zero {r['longest_zero_run_ms']:.1f} ms   "
                  f"silence {r['silence_pct']:.1f}%")
            snr = r["snr_db"]
            print(f"        SNR ~{snr:.1f} dB" if snr == snr else "        SNR n/a", end="")
            print(f"   LF<100Hz {100*r['lf_frac']:.1f}%   speech300-3400 {100*r['speech_frac']:.1f}%"
                  f"   HF>4k {100*r['hf_frac']:.1f}%   centroid {r['centroid_hz']:.0f} Hz")
            if "duration_drift_pct" in r:
                print(f"        length drift {r['duration_drift_pct']:+.2f}%")
        for m in r["fails"]:
            print(f"        {BAD} {m}")
        for m in r["warns"]:
            print(f"        {WARN} {m}")
        print()
        n_fail += bool(r["fails"])
        n_warn += bool(r["warns"] and not r["fails"])
        if args.plot:
            plot(f, f.parent / "qc")

    print("=" * 78)
    print(f"{len(files) - n_fail}/{len(files)} passed   "
          f"({n_warn} with warnings, {n_fail} failed)")
    if n_fail:
        print("\nRESULT: FAIL — fix before collecting data.")
        return 1
    print("\nRESULT: PASS — all required checks met.")
    if n_warn:
        print("        Warnings are advisory; review them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
