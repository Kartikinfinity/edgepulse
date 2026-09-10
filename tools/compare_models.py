#!/usr/bin/env python3
"""Compare two KWS models on the SAME held-out real test set.

    python tools/compare_models.py \
        --a artifacts/model_1_baseline --a-label "model-1 (synthetic only)" \
        --b artifacts/model_2_domain   --b-label "model-2 (+ real INMP441)" \
        --dataset data/dataset_v3

Rules this script enforces, because they are the ones easy to break by accident:

  * Each model is scored with ITS OWN normalisation statistics. Sharing them
    silently invalidates the comparison.
  * The operating threshold is chosen on VALIDATION, per model, and then applied
    unchanged to test. Nothing is swept on test labels.
  * Streaming detection over raw unmodified recordings is reported alongside the
    clip metrics and is the primary number. Clip construction can flatter a
    model; a continuous recording cannot.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import ARTIFACTS_DIR, DATASET_ROOT, RECORDINGS_ROOT  # noqa: E402
from training import features as F  # noqa: E402
from training.dataset import load_split, subset_mask  # noqa: E402
from training.streaming_eval import (build_negative_stream, detections,  # noqa: E402
                                     load_pcm, stream_scores)

OUT = ARTIFACTS_DIR / "comparison"
FA_TARGET_PER_HOUR = 1.0


def load(model_dir: Path):
    import tensorflow as tf
    m = tf.keras.models.load_model(model_dir / "kws_float.keras")
    nz = np.load(model_dir / "normalisation.npz")
    return m, nz["mean"][:, None], nz["std"][:, None]


def scores(model, X, m4, s4) -> np.ndarray:
    return model.predict(F.apply_normalisation(X, m4, s4), batch_size=256,
                         verbose=0)[:, 0]


def pick_threshold(p_pos: np.ndarray, p_neg: np.ndarray,
                   target_far: float = 0.01) -> float:
    """Lowest threshold whose false-accept rate on VALIDATION negatives stays
    under target_far. Chosen on validation, never on test."""
    if p_neg.size == 0:
        return 0.5
    thr = float(np.quantile(p_neg, 1.0 - target_far))
    return float(min(max(thr, 0.05), 0.99))


def real_recordings() -> list[Path]:
    return sorted(RECORDINGS_ROOT.rglob("*takshila*.wav"))


def evaluate(model_dir: Path, label: str, dataset: Path, minutes: float,
             heldout_session: str) -> dict:
    model, m4, s4 = load(model_dir)
    va = load_split("validation", dataset, log=lambda *a: None)
    te = load_split("test", dataset, log=lambda *a: None)
    pva, pte = scores(model, va["X"], m4, s4), scores(model, te["X"], m4, s4)

    # ---- threshold from VALIDATION only -----------------------------------
    neg_va = subset_mask(va["rows"], model_target=("unknown", "background"))
    thr = pick_threshold(pva[~neg_va], pva[neg_va])

    r: dict = {"label": label, "model_dir": str(model_dir), "threshold": round(thr, 4)}

    # ---- clip metrics on TEST ---------------------------------------------
    rows = te["rows"]
    def grp(**kw):
        mk = subset_mask(rows, **kw)
        return pte[mk], int(mk.sum())

    p_real, n_real = grp(**{"class": "positive", "synthetic": "false"})
    r["real_positives"] = {
        "n": n_real,
        "median_score": float(np.median(p_real)) if n_real else None,
        "recall": float((p_real >= thr).mean()) if n_real else None,
        "frr": float((p_real < thr).mean()) if n_real else None,
        "detected": int((p_real >= thr).sum()) if n_real else 0,
    }
    for key, sel in (("near_homophone", {"class": "near_homophone"}),
                     ("hard_negative", {"class": "hard_negative"}),
                     ("speech_negative", {"class": "speech_negative"})):
        p, n = grp(**sel)
        r[key] = {"n": n,
                  "false_accepts": int((p >= thr).sum()) if n else 0,
                  "rejected_pct": float((p < thr).mean() * 100) if n else None,
                  "median_score": float(np.median(p)) if n else None}

    # ---- confidence distribution -----------------------------------------
    if n_real:
        r["real_score_percentiles"] = {f"p{q}": float(np.percentile(p_real, q))
                                       for q in (10, 25, 50, 75, 90)}

    # ---- threshold curve (reported, NOT used to pick) ---------------------
    curve = []
    neg_te = subset_mask(rows, model_target=("unknown", "background"))
    for t in np.arange(0.05, 1.0, 0.05):
        curve.append({
            "threshold": round(float(t), 2),
            "real_recall": float((p_real >= t).mean()) if n_real else None,
            "neg_false_accept_pct": float((pte[neg_te] >= t).mean() * 100),
        })
    r["threshold_curve"] = curve

    # ---- streaming over raw recordings: the primary number ----------------
    # Reported for BOTH inference paths. The factory peak-normalises every
    # positive to -6 dBFS while the streaming path fed raw audio 16 dB quieter,
    # so "does it detect?" has a different answer depending on which path runs
    # (EXP-007). Showing one and not the other would hide the finding.
    nz = np.load(model_dir / "normalisation.npz")
    mean, std = nz["mean"], nz["std"]
    files = real_recordings()
    heldout = [f for f in files if f.parent.name == heldout_session]
    r["streaming_heldout"] = {"session": heldout_session, "n_recordings": len(heldout)}
    for norm in (False, True):
        det, peaks, lat = 0, [], []
        for f in heldout:
            pcm = load_pcm(f)
            t0 = time.time()
            times, sc = stream_scores(model, pcm, mean, std, level_normalise=norm)
            lat.append((time.time() - t0) / max(1, len(times)) * 1000)
            peaks.append(float(sc.max()) if sc.size else 0.0)
            if detections(times, sc, thr):
                det += 1
        r["streaming_heldout"]["level_normalised" if norm else "raw"] = {
            "detected": det,
            "detection_rate": float(det / len(heldout)) if heldout else None,
            "median_peak_score": float(np.median(peaks)) if peaks else None,
            "host_ms_per_window": float(np.median(lat)) if lat else None,
        }

    # ---- false accepts per hour on continuous negative audio ---------------
    stream = build_negative_stream(dataset, minutes)
    times, sc = stream_scores(model, stream, mean, std)
    fa = len(detections(times, sc, thr))
    hours = stream.size / F.SAMPLE_RATE / 3600.0
    r["false_accepts"] = {
        "minutes_of_audio": round(minutes, 1),
        "count": fa,
        "per_hour": round(fa / hours, 2) if hours > 0 else None,
    }
    return r


def fmt(v, nd=3, pct=False):
    if v is None:
        return "n/a"
    if pct:
        return f"{v*100:.1f}%" if v <= 1.0 else f"{v:.1f}%"
    return f"{v:.{nd}f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", type=Path, required=True)
    ap.add_argument("--b", type=Path, required=True)
    ap.add_argument("--a-label", default="model-1")
    ap.add_argument("--b-label", default="model-2")
    ap.add_argument("--dataset", type=Path, default=DATASET_ROOT)
    ap.add_argument("--minutes", type=float, default=15.0)
    ap.add_argument("--heldout-session", default="")
    args = ap.parse_args()

    heldout = args.heldout_session
    if not heldout:
        import csv
        with (args.dataset / "manifests" / "test.csv").open(encoding="utf-8") as fh:
            s = {r.get("session_id", "") for r in csv.DictReader(fh)}
        s.discard("")
        if len(s) != 1:
            raise SystemExit(f"cannot infer the held-out session (found {sorted(s)}); "
                             "pass --heldout-session")
        heldout = s.pop()

    print("=" * 78)
    print("MODEL COMPARISON - same held-out real test set")
    print("=" * 78)
    print(f"  dataset          {args.dataset}")
    print(f"  held-out session {heldout}")
    print("  threshold per model chosen on VALIDATION, applied unchanged to test\n")

    A = evaluate(args.a, args.a_label, args.dataset, args.minutes, heldout)
    B = evaluate(args.b, args.b_label, args.dataset, args.minutes, heldout)

    w = 30
    def row(name, va, vb):
        print(f"  {name:<{w}}{va:>21}{vb:>21}")

    print(f"  {'':<{w}}{A['label']:>21}{B['label']:>21}")
    print("  " + "-" * (w + 42))
    row("operating threshold", fmt(A["threshold"]), fmt(B["threshold"]))
    print()
    print("  REAL INMP441 POSITIVES (held-out session, clip level)")
    row("  n", str(A["real_positives"]["n"]), str(B["real_positives"]["n"]))
    row("  median score", fmt(A["real_positives"]["median_score"]),
        fmt(B["real_positives"]["median_score"]))
    row("  recall", fmt(A["real_positives"]["recall"], pct=True),
        fmt(B["real_positives"]["recall"], pct=True))
    row("  FRR", fmt(A["real_positives"]["frr"], pct=True),
        fmt(B["real_positives"]["frr"], pct=True))
    print()
    print("  STREAMING over raw held-out recordings  <-- PRIMARY METRIC")
    for key, lbl in (("raw", "raw (current firmware contract)"),
                     ("level_normalised", "+ per-window level normalisation")):
        a, b = A["streaming_heldout"][key], B["streaming_heldout"][key]
        n = A["streaming_heldout"]["n_recordings"]
        row(f"  {lbl}", f"{a['detected']}/{n}", f"{b['detected']}/{n}")
        row("    median peak score", fmt(a["median_peak_score"]),
            fmt(b["median_peak_score"]))
    row("  host ms/window", fmt(A["streaming_heldout"]["raw"]["host_ms_per_window"], 2),
        fmt(B["streaming_heldout"]["raw"]["host_ms_per_window"], 2))
    print()
    print("  NEGATIVES (test)")
    for k, nm in (("near_homophone", "near-homophone"),
                  ("hard_negative", "hard negative"),
                  ("speech_negative", "speech negative")):
        row(f"  {nm} rejected", fmt(A[k]["rejected_pct"], 1, pct=True),
            fmt(B[k]["rejected_pct"], 1, pct=True))
    row("  false accepts / hour", fmt(A["false_accepts"]["per_hour"], 2),
        fmt(B["false_accepts"]["per_hour"], 2))

    OUT.mkdir(parents=True, exist_ok=True)
    rec = {"compared_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "dataset": str(args.dataset), "heldout_session": heldout,
           "models": [A, B]}
    (OUT / "model_comparison.json").write_text(json.dumps(rec, indent=2) + "\n",
                                               encoding="utf-8")
    print(f"\nwrote {OUT / 'model_comparison.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
