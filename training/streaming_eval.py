#!/usr/bin/env python3
"""Streaming detection: the way the device actually runs.

    python training/streaming_eval.py

A clip metric answers "given a 1.0 s window centred on a word, what is it?".
The device is never handed a centred window. It slides a 985 ms context over an
unbroken audio stream and runs inference every 200 ms, forever, and every one of
those inferences is a chance to fire on something that is not the keyword.
Those are different questions with different answers, and conflating them is the
single most expensive mistake this project has on record (DECISIONS.md D-005).

This harness measures, on continuous audio:
  * false accepts per HOUR on negative audio
  * detection rate on real recordings that contain the keyword
  * wake latency, from keyword offset to the firing inference

Detection logic mirrors the planned firmware: score every INFER_HOP_FRAMES, fire
when M of the last N inferences exceed the threshold, then hold off for a
refractory period so one utterance cannot register as several detections.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import ARTIFACTS_DIR, DATASET_ROOT, RECORDINGS_ROOT  # noqa: E402
from training import features as F  # noqa: E402
from training.dataset import read_manifest  # noqa: E402
from training.model import KEYWORD_IDX  # noqa: E402

OUT = ARTIFACTS_DIR / "model"

INFER_HOP_FRAMES = 10          # 10 frames * 20 ms = 200 ms cadence (D-012)
SMOOTH_M, SMOOTH_N = 2, 3      # fire on 2 of the last 3 inferences
REFRACTORY_MS = 1000           # one utterance = at most one detection


def stream_scores(model, pcm: np.ndarray, mean, std,
                  level_normalise: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Slide the real streaming front end over `pcm`.

    Returns (times_ms, scores): the wall-clock time of each inference, measured
    at the END of its 985 ms context - which is the instant the device would
    have the information - and P(keyword) at that instant.
    """
    fe = F.StreamingFrontEnd(level_normalise=level_normalise)
    windows, times = [], []
    n_frames = 0
    chunk = F.FRAME_HOP
    for i in range(0, pcm.size, chunk):
        for _ in fe.push(pcm[i:i + chunk]):
            n_frames += 1
            if fe.ready and n_frames % INFER_HOP_FRAMES == 0:
                windows.append(fe.window())
                # the newest frame spans [t-25ms, t]; its end is the decision time
                times.append((n_frames - 1) * F.FRAME_HOP / F.SAMPLE_RATE * 1000
                             + F.FRAME_LEN / F.SAMPLE_RATE * 1000)
    if not windows:
        return np.zeros(0), np.zeros(0)
    X = np.asarray(windows, dtype=np.float32)[..., None]
    X = F.apply_normalisation(X, mean[:, None], std[:, None])
    p = model.predict(X, batch_size=256, verbose=0)[:, KEYWORD_IDX]
    return np.asarray(times), p


def detections(times: np.ndarray, scores: np.ndarray, thr: float) -> list[float]:
    """Apply M-of-N smoothing plus a refractory hold. Returns firing times (ms)."""
    fired, last = [], -1e9
    hits = scores >= thr
    for i in range(len(scores)):
        lo = max(0, i - SMOOTH_N + 1)
        if hits[lo:i + 1].sum() >= SMOOTH_M and times[i] - last >= REFRACTORY_MS:
            fired.append(float(times[i]))
            last = times[i]
    return fired


def load_pcm(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != F.SAMPLE_RATE or w.getsampwidth() != 2:
            raise ValueError(f"{path}: expected 16 kHz 16-bit")
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    if w.getnchannels() > 1:
        x = x.reshape(-1, w.getnchannels()).mean(axis=1).astype(np.int16)
    return x


def build_negative_stream(dataset: Path, minutes: float, seed: int = 20260910) -> np.ndarray:
    """Concatenate TEST-split negatives into one long stream.

    Concatenation is a proxy for naturally continuous audio: the joins are
    artificial and the harness must not pretend otherwise. It is still far
    closer to the device's experience than isolated clip scoring, and every
    negative used here is one the model has never seen.
    """
    rows = [r for r in read_manifest("test", dataset) if r["model_target"] != "keyword"]
    rng = np.random.default_rng(seed)
    rng.shuffle(rows)
    need = int(minutes * 60 * F.SAMPLE_RATE)
    parts, total = [], 0
    for r in rows:
        if total >= need:
            break
        x = load_pcm(dataset / r["filepath"])
        parts.append(x)
        total += x.size
    return np.concatenate(parts) if parts else np.zeros(0, dtype=np.int16)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=DATASET_ROOT)
    ap.add_argument("--model", type=Path, default=OUT / "kws_float.keras")
    ap.add_argument("--minutes", type=float, default=15.0,
                    help="length of the continuous negative stream")
    args = ap.parse_args()

    import tensorflow as tf
    model = tf.keras.models.load_model(args.model)
    norm = np.load(args.model.parent / "normalisation.npz")
    mean, std = norm["mean"], norm["std"]

    clip_eval = json.loads((OUT / "evaluation_clip.json").read_text(encoding="utf-8"))
    thr = clip_eval["threshold"]

    print("=" * 78)
    print("STREAMING EVALUATION - continuous audio, device cadence")
    print("=" * 78)
    print(f"  threshold        {thr:.3f}   (chosen on VALIDATION, reused unchanged)")
    print(f"  inference every  {INFER_HOP_FRAMES * F.FRAME_HOP / F.SAMPLE_RATE * 1000:.0f} ms")
    print(f"  smoothing        {SMOOTH_M} of {SMOOTH_N}, refractory {REFRACTORY_MS} ms")

    # ---- false accepts on continuous negative audio -----------------------
    print(f"\nbuilding a {args.minutes:.0f} min negative stream from TEST negatives")
    neg = build_negative_stream(args.dataset, args.minutes)
    hours = neg.size / F.SAMPLE_RATE / 3600
    t0 = time.time()
    tms, sc = stream_scores(model, neg, mean, std)
    fires = detections(tms, sc, thr)
    fa_per_hour = len(fires) / hours if hours else float("nan")
    print(f"  stream           {neg.size / F.SAMPLE_RATE / 60:.1f} min "
          f"({len(sc):,} inferences, {time.time() - t0:.0f}s to score)")
    print(f"  false accepts    {len(fires)}")
    print(f"  FA / hour        {fa_per_hour:.2f}")
    # A count is Poisson; with a handful of events the interval is wide and
    # quoting the point estimate alone would overstate what 15 min can show.
    k = len(fires)
    lo = 0.0 if k == 0 else (k * (1 - 1 / (9 * k) - 1.96 / (3 * np.sqrt(k))) ** 3)
    hi = (k + 1) * (1 - 1 / (9 * (k + 1)) + 1.96 / (3 * np.sqrt(k + 1))) ** 3
    print(f"  95% CI           {lo / hours:.2f} - {hi / hours:.2f} FA/hour "
          f"(Poisson, {k} events in {hours * 60:.0f} min)")

    # ---- detection on real recordings that contain the keyword ------------
    print("\nreal INMP441 recordings containing 'Takshila':")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.dataset_factory.audio import read_wav, speech_span_bounds  # noqa: E402
    from tools.dataset_factory.config import SR  # noqa: E402

    per_session: dict[str, list] = {}
    for wav in sorted(RECORDINGS_ROOT.rglob("*takshila*.wav")):
        xf, _ = read_wav(wav)
        b = speech_span_bounds(xf, SR)
        if b is None:
            continue
        span_ms = (b[1] - b[0]) / SR * 1000
        if not (250 <= span_ms <= 880):
            continue                       # not a clean single utterance
        pcm = load_pcm(wav)
        tms, sc = stream_scores(model, pcm, mean, std)
        fires = detections(tms, sc, thr)
        onset_ms, offset_ms = b[0] / SR * 1000, b[1] / SR * 1000
        # A fire counts if it lands between the word starting and 1.5 s after it
        # ends: earlier is impossible, much later is a coincidence, not a wake.
        hit = [f for f in fires if onset_ms <= f <= offset_ms + 1500]
        sess = wav.parent.name
        per_session.setdefault(sess, []).append({
            "file": wav.name,
            "detected": bool(hit),
            "latency_ms": (hit[0] - offset_ms) if hit else None,
            "peak_score": float(sc.max()) if sc.size else 0.0,
            "spurious": len(fires) - len(hit),
        })

    all_takes = [t for v in per_session.values() for t in v]
    n_det = sum(t["detected"] for t in all_takes)
    lat = [t["latency_ms"] for t in all_takes if t["latency_ms"] is not None]
    for sess, takes in sorted(per_session.items()):
        d = sum(t["detected"] for t in takes)
        print(f"  {sess:<14} {d}/{len(takes)} detected   "
              f"peak score med {np.median([t['peak_score'] for t in takes]):.3f}")
    if all_takes:
        print(f"  TOTAL          {n_det}/{len(all_takes)} detected "
              f"({n_det / len(all_takes):.1%})")
    if lat:
        print(f"  wake latency   median {np.median(lat):.0f} ms   "
              f"min {min(lat):.0f}   max {max(lat):.0f}   (from keyword offset)")
    else:
        print("  wake latency   not measurable - nothing was detected")

    rec = {
        "evaluated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "threshold": thr,
        "threshold_source": "validation split, via evaluate.py - NOT retuned here",
        "cadence_ms": INFER_HOP_FRAMES * F.FRAME_HOP / F.SAMPLE_RATE * 1000,
        "smoothing": {"m": SMOOTH_M, "n": SMOOTH_N, "refractory_ms": REFRACTORY_MS},
        "false_accepts": {
            "stream_minutes": neg.size / F.SAMPLE_RATE / 60,
            "inferences": int(len(sc)),
            "count": k,
            "per_hour": fa_per_hour,
            "per_hour_ci95": [lo / hours if hours else None,
                              hi / hours if hours else None],
            "stream_composition": "TEST-split negatives, shuffled and concatenated",
        },
        "detection": {
            "takes": len(all_takes), "detected": int(n_det),
            "rate": n_det / len(all_takes) if all_takes else None,
            "latency_ms_median": float(np.median(lat)) if lat else None,
            "latency_ms_min": float(min(lat)) if lat else None,
            "latency_ms_max": float(max(lat)) if lat else None,
            "per_session": per_session,
        },
        "what_this_does_not_prove": [
            "The negative stream is concatenated clips, not naturally continuous "
            "room audio; join boundaries are artificial.",
            "All positive takes come from ONE speaker on ONE microphone. This is "
            "not a speaker-independent detection rate.",
            "Latency is host-side and excludes I2S DMA, on-device MFCC and TFLM "
            "invoke time - measure those on the board.",
            "FA/hour rests on a Poisson count over minutes, not hours.",
        ],
    }
    (OUT / "evaluation_streaming.json").write_text(json.dumps(rec, indent=2) + "\n",
                                                   encoding="utf-8")
    print(f"\nwrote {OUT / 'evaluation_streaming.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
