#!/usr/bin/env python3
"""Produce golden feature vectors — the host/device parity contract.

    python tools/make_golden_features.py

Writes artifacts/golden/ containing, for a handful of fixed inputs:
  * the input PCM as a 16-bit WAV and as a C array
  * the 49x13 MFCC the host produces, as .npy, .csv and a C array
  * a JSON manifest with the pipeline configuration and per-case checksums

The firmware runs the same inputs through its own MFCC and compares. Until that
comparison passes, no on-device accuracy claim means anything
(`ARCHITECTURE.md` 3: "a host/device parity test must pass ... before any
on-device accuracy claim"). The bar to beat is the prior build's max abs diff
0.000112 / correlation 1.0000000000.

Cases are chosen to exercise different parts of the pipeline, not to look good:
silence (log floor), DC (mel floor), tones at band edges, an impulse (spectral
leakage), full-scale noise (clipping headroom), and REAL keyword audio.
"""

from __future__ import annotations

import hashlib
import json
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import ARTIFACTS_DIR, RECORDINGS_ROOT  # noqa: E402
from training import features as F  # noqa: E402

OUT = ARTIFACTS_DIR / "golden"


def sine(freq: float, n: int = F.CLIP_SAMPLES, amp: float = 0.25) -> np.ndarray:
    t = np.arange(n) / F.SAMPLE_RATE
    return (amp * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)


def build_cases() -> list[tuple[str, np.ndarray, str]]:
    n = F.CLIP_SAMPLES
    rng = np.random.default_rng(20260910)
    cases: list[tuple[str, np.ndarray, str]] = [
        ("silence", np.zeros(n, dtype=np.int16),
         "digital silence - exercises the log floor; must stay finite"),
        ("dc_offset", np.full(n, 3000, dtype=np.int16),
         "constant DC - all energy below the 125 Hz mel floor, so near-silent output"),
        ("tone_1000hz", sine(1000.0),
         "mid-band tone - the reference case"),
        ("tone_125hz", sine(125.0),
         "exactly the low mel edge"),
        ("tone_7500hz", sine(7500.0),
         "exactly the high mel edge"),
        ("tone_4000hz", sine(4000.0),
         "in the band the INMP441 resolves most cleanly, where /SH/ lives"),
        ("burst", np.zeros(n, dtype=np.int16),
         "8-sample full-scale burst - spectral leakage without depending on "
         "where the Hann window happens to be zero"),
        ("white_noise", (rng.normal(0, 0.1, n).clip(-1, 1) * 32767).astype(np.int16),
         "broadband, seeded"),
        ("chirp", (0.3 * np.sin(2 * np.pi * np.cumsum(
            np.linspace(100, 7000, n)) / F.SAMPLE_RATE) * 32767).astype(np.int16),
         "sweep 100-7000 Hz - walks every mel filter in turn"),
        ("full_scale", (np.sign(rng.normal(0, 1, n)) * 32767).astype(np.int16),
         "full-scale square-ish - headroom and clipping behaviour"),
    ]
    # A LONE sample can land exactly where the Hann window is 0.0 and be erased.
    # A short burst always survives windowing while still being broadband.
    cases[6][1][n // 2: n // 2 + 8] = 32767

    # Real keyword audio, if a usable recording exists. A synthetic-only golden
    # set would not exercise the pipeline on the signal that actually matters.
    real = sorted(RECORDINGS_ROOT.rglob("*takshila*.wav"))
    added = 0
    for f in real:
        if added >= 2:
            break
        try:
            with wave.open(str(f), "rb") as w:
                if w.getframerate() != F.SAMPLE_RATE or w.getsampwidth() != 2:
                    continue
                x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        except Exception:
            continue
        # centre a 1.0 s window on the loudest part
        if x.size > F.CLIP_SAMPLES:
            fr = 320
            m = x.size // fr
            e = (x[:m * fr].astype(np.float64).reshape(m, fr) ** 2).mean(axis=1)
            c = int(np.argmax(e)) * fr
            s = max(0, min(x.size - F.CLIP_SAMPLES, c - F.CLIP_SAMPLES // 2))
            x = x[s:s + F.CLIP_SAMPLES]
        if x.size != F.CLIP_SAMPLES:
            continue
        cases.append((f"real_keyword_{added+1}", x.copy(),
                      f"real INMP441 audio from {f.name}"))
        added += 1
    return cases


def c_array(name: str, arr: np.ndarray, dtype: str, per_line: int = 8) -> str:
    flat = arr.ravel()
    lines = [f"const {dtype} {name}[{flat.size}] = {{"]
    for i in range(0, flat.size, per_line):
        chunk = flat[i:i + per_line]
        if dtype.startswith("int16"):
            body = ", ".join(f"{int(v):6d}" for v in chunk)
        else:
            body = ", ".join(f"{float(v):+.8e}f" for v in chunk)
        lines.append("    " + body + ("," if i + per_line < flat.size else ""))
    lines.append("};")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    manifest = {
        "purpose": "host/device MFCC parity reference",
        "pipeline": F.describe(),
        "parity_bar": {
            "max_abs_diff": 1e-3,
            "min_correlation": 0.9999,
            "note": "prior build achieved 0.000112 / 1.0000000000 on this pipeline",
        },
        "cases": [],
    }

    silence_ref = None          # case 0 is silence; every other case is compared to it
    print(f"writing {len(cases)} golden cases to {OUT}")
    for name, pcm, why in cases:
        feats = F.clip_features(pcm)                     # (49, 13) float32
        stream = F.frames_streaming(pcm)[:F.N_FRAMES]
        drift = float(np.abs(feats - stream.astype(np.float32)).max())

        np.save(OUT / f"{name}_input.npy", pcm)
        np.save(OUT / f"{name}_mfcc.npy", feats)
        with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(F.SAMPLE_RATE)
            w.writeframes(pcm.tobytes())
        np.savetxt(OUT / f"{name}_mfcc.csv", feats, delimiter=",", fmt="%.8e")

        # A golden case is useful if its output is DISTINGUISHABLE FROM SILENCE.
        # Frame-to-frame variation is the wrong test: a steady tone legitimately
        # produces 49 identical frames, and flagging that as degenerate is a
        # false positive on every stationary case.
        frame_spread = float(feats.std(axis=0).mean())
        if silence_ref is None:
            dist_from_silence = 0.0
        else:
            dist_from_silence = float(np.abs(feats.mean(axis=0)
                                             - silence_ref).max())
        manifest["cases"].append({
            "name": name,
            "frame_spread": frame_spread,
            "max_abs_diff_vs_silence": dist_from_silence,
            "description": why,
            "input_sha256": hashlib.sha256(pcm.tobytes()).hexdigest(),
            "mfcc_sha256": hashlib.sha256(feats.tobytes()).hexdigest(),
            "mfcc_shape": list(feats.shape),
            "mfcc_min": float(feats.min()), "mfcc_max": float(feats.max()),
            "mfcc_mean": float(feats.mean()),
            "c0_first": float(feats[0, 0]), "c0_last": float(feats[-1, 0]),
            "streaming_vs_batch_max_abs_diff": drift,
        })
        if silence_ref is None:
            silence_ref = feats.mean(axis=0)          # first case IS silence
            flag = "  (reference)"
        else:
            flag = "  <-- DEGENERATE: same as silence" if dist_from_silence < 1e-3 else ""
        print(f"  {name:<16} range [{feats.min():8.2f},{feats.max():7.2f}]  "
              f"vs-silence {dist_from_silence:8.2f}  frame-spread {frame_spread:5.2f}  "
              f"drift {drift:.0e}{flag}")

    (OUT / "golden_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # One C header the firmware can include directly for its parity self-test.
    ref = cases[2]                                       # tone_1000hz
    ref_f = F.clip_features(ref[1])
    hdr = [
        "// AUTO-GENERATED by tools/make_golden_features.py - DO NOT EDIT.",
        "// Host reference for the on-device MFCC parity test.",
        "// Case: " + ref[0] + " - " + ref[2],
        "#pragma once",
        "#include <stdint.h>",
        "",
        f"#define GOLDEN_SAMPLE_RATE {F.SAMPLE_RATE}",
        f"#define GOLDEN_CLIP_SAMPLES {F.CLIP_SAMPLES}",
        f"#define GOLDEN_N_FRAMES {F.N_FRAMES}",
        f"#define GOLDEN_N_MFCC {F.N_MFCC}",
        "",
        c_array("golden_input_pcm", ref[1], "int16_t"),
        "",
        c_array("golden_expected_mfcc", ref_f, "float"),
        "",
    ]
    (OUT / "golden_reference.h").write_text("\n".join(hdr), encoding="utf-8")

    total = sum(f.stat().st_size for f in OUT.iterdir() if f.is_file())
    print(f"\nwrote {len(list(OUT.iterdir()))} files ({total/1e6:.1f} MB) to {OUT}")
    print("  golden_manifest.json  - config + per-case checksums")
    print("  golden_reference.h    - C header for the firmware parity self-test")
    print("\nParity bar: max abs diff < 1e-3 AND correlation > 0.9999")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
