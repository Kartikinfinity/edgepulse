#!/usr/bin/env python3
"""Measure the trained Takshila model. Clip-level metrics and the operating point.

    python training/evaluate.py

THE RULE THIS SCRIPT EXISTS TO ENFORCE: the detection threshold is chosen on the
VALIDATION split and then applied ONCE to TEST. Sweeping a threshold on test and
reporting the best point is not a result, it is a description of the test set
(CLAUDE.md safety rule 3).

What this does NOT prove: these are CLIP metrics on centred 1.0 s windows. The
device sees a sliding window over continuous audio. Streaming detection, false
accepts per hour and wake latency are measured by training/streaming_eval.py,
and a clip number must never be quoted as a detector number (DECISIONS.md D-005).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import ARTIFACTS_DIR, DATASET_ROOT  # noqa: E402
from training import features as F  # noqa: E402
from training.dataset import load_split, subset_mask  # noqa: E402
from training.model import CLASS_NAMES, KEYWORD_IDX, summarise  # noqa: E402

OUT = ARTIFACTS_DIR / "model"

# Declared BEFORE looking at any test number.
TARGET_FA_RATE = 0.01          # <=1% of negative clips may score above threshold
SWEEP = np.round(np.arange(0.05, 0.996, 0.005), 3)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. The normal approximation breaks down at k=0 or
    k=n, which is exactly where small positive sets live."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def score(model, X: np.ndarray, batch: int = 256) -> np.ndarray:
    """P(keyword) for every clip."""
    return model.predict(X, batch_size=batch, verbose=0)[:, KEYWORD_IDX]


def sweep_validation(p: np.ndarray, y: np.ndarray) -> dict:
    """Pick the operating point on VALIDATION. Returns the chosen threshold and
    the whole curve, so the choice is auditable rather than asserted."""
    pos, neg = y == KEYWORD_IDX, y != KEYWORD_IDX
    n_pos, n_neg = int(pos.sum()), int(neg.sum())
    curve = []
    for t in SWEEP:
        tp = int((p[pos] >= t).sum())
        fa = int((p[neg] >= t).sum())
        recall = tp / n_pos if n_pos else float("nan")
        fa_rate = fa / n_neg if n_neg else float("nan")
        prec = tp / (tp + fa) if (tp + fa) else 0.0
        f1 = 2 * prec * recall / (prec + recall) if (prec + recall) else 0.0
        curve.append({"threshold": float(t), "recall": recall, "frr": 1 - recall,
                      "fa_rate": fa_rate, "precision": prec, "f1": f1})

    # Primary rule: the LOWEST threshold whose false-accept rate meets target.
    # Lowest, because among thresholds that all satisfy the FA budget, the one
    # with the most recall is the right pick.
    ok = [c for c in curve if c["fa_rate"] <= TARGET_FA_RATE]
    chosen = min(ok, key=lambda c: c["threshold"]) if ok else max(curve, key=lambda c: c["f1"])
    return {"curve": curve, "chosen": chosen, "rule_met": bool(ok),
            "best_f1": max(curve, key=lambda c: c["f1"]),
            "n_pos": n_pos, "n_neg": n_neg}


def confusion(y: np.ndarray, yhat: np.ndarray) -> np.ndarray:
    m = np.zeros((len(CLASS_NAMES), len(CLASS_NAMES)), dtype=int)
    for a, b in zip(y, yhat):
        m[a, b] += 1
    return m


def per_subset(rows, p, thr) -> list[dict]:
    """False accepts broken out by the negative tier that produced them, and
    recall broken out by whether the positive was real or synthetic."""
    out = []
    groups = [
        ("positives - real INMP441", {"class": "positive", "synthetic": "false"}),
        ("positives - synthetic TTS", {"class": "positive", "synthetic": "true"}),
        ("near_homophone", {"class": "near_homophone"}),
        ("hard_negative", {"class": "hard_negative"}),
        ("speech_negative", {"class": "speech_negative"}),
        ("background", {"class": "background"}),
        ("silence", {"class": "silence"}),
    ]
    for name, cond in groups:
        m = subset_mask(rows, **cond)
        n = int(m.sum())
        if n == 0:
            continue
        fired = int((p[m] >= thr).sum())
        is_pos = name.startswith("positives")
        # For positives the interesting count is detections; for negatives it is
        # correct rejections. Both are reported as "value" with the metric named.
        k = fired if is_pos else n - fired
        lo, hi = wilson(k, n)
        n_utt = None
        if is_pos:
            n_utt = len({(r.get("speaker_id", ""), r.get("voice_id", ""),
                          r.get("text", ""), r.get("keyword_onset_ms", ""))
                         for r, keep in zip(rows, m) if keep})
        out.append({
            "subset": name, "n": n, "fired": fired, "rate": fired / n,
            "metric": "recall" if is_pos else "correct_reject",
            "value": k / n, "ci95": [lo, hi], "n_utterances": n_utt,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=DATASET_ROOT)
    ap.add_argument("--model", type=Path, default=OUT / "kws_float.keras")
    args = ap.parse_args()

    import tensorflow as tf
    model = tf.keras.models.load_model(args.model)
    norm = np.load(OUT / "normalisation.npz")
    m4, s4 = norm["mean"][:, None], norm["std"][:, None]

    print("=" * 78)
    print("EVALUATION - Takshila baseline, CLIP LEVEL")
    print("=" * 78)

    va = load_split("validation", args.dataset)
    te = load_split("test", args.dataset)
    Xva = F.apply_normalisation(va["X"], m4, s4)
    Xte = F.apply_normalisation(te["X"], m4, s4)

    pva, pte = score(model, Xva), score(model, Xte)
    yva, yte = va["y"], te["y"]

    # ---- operating point, on validation ONLY ------------------------------
    sw = sweep_validation(pva, yva)
    thr = sw["chosen"]["threshold"]
    print(f"\nTHRESHOLD SELECTION (validation only, {sw['n_pos']} pos / {sw['n_neg']} neg)")
    print(f"  rule           lowest threshold with FA rate <= {TARGET_FA_RATE:.1%}")
    print(f"  rule satisfied {sw['rule_met']}")
    print(f"  chosen         {thr:.3f}   recall {sw['chosen']['recall']:.4f}  "
          f"FA {sw['chosen']['fa_rate']:.4f}  F1 {sw['chosen']['f1']:.4f}")
    print(f"  (best-F1 point {sw['best_f1']['threshold']:.3f} -> F1 "
          f"{sw['best_f1']['f1']:.4f}; NOT used, shown for context)")

    # ---- apply once to test -----------------------------------------------
    results = {}
    for name, p, y, rows, X in (("validation", pva, yva, va["rows"], Xva),
                                ("test", pte, yte, te["rows"], Xte)):
        pos, neg = y == KEYWORD_IDX, y != KEYWORD_IDX
        n_pos, n_neg = int(pos.sum()), int(neg.sum())
        tp = int((p[pos] >= thr).sum())
        fn = n_pos - tp
        fp = int((p[neg] >= thr).sum())
        tn = n_neg - fp
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / n_pos if n_pos else float("nan")
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        rlo, rhi = wilson(tp, n_pos)
        yhat = np.argmax(model.predict(X, batch_size=256, verbose=0), axis=1)
        cm = confusion(y, yhat)
        subs = per_subset(rows, p, thr)
        results[name] = {
            "threshold": thr, "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "n_positive_clips": n_pos, "n_negative_clips": n_neg,
            "precision": prec, "recall": rec, "f1": f1,
            "frr": 1 - rec if n_pos else float("nan"),
            "far": fp / n_neg if n_neg else float("nan"),
            "recall_ci95": [rlo, rhi],
            "argmax_accuracy": float((yhat == y).mean()),
            "confusion_matrix": cm.tolist(),
            "subsets": subs,
        }
        print(f"\n{'-' * 78}")
        print(f"{name.upper()}  (threshold {thr:.3f})")
        print(f"  TP {tp:<6} FN {fn:<6} FP {fp:<6} TN {tn}")
        print(f"  precision {prec:.4f}   recall {rec:.4f} "
              f"[95% CI {rlo:.3f}-{rhi:.3f}]   F1 {f1:.4f}")
        print(f"  FRR {1 - rec:.4f}   FA rate {fp / max(1, n_neg):.4f}   "
              f"argmax acc {(yhat == y).mean():.4f}")
        print(f"  confusion (rows = true {list(CLASS_NAMES)}):")
        for i, r in enumerate(cm):
            print(f"    {CLASS_NAMES[i]:<11} " + "  ".join(f"{v:>6d}" for v in r))
        print("  by subset:")
        for s in subs:
            u = f"  ({s['n_utterances']} distinct utterances)" if s["n_utterances"] else ""
            print(f"    {s['subset']:<26} n={s['n']:<6} {s['metric']} "
                  f"{s['value']:.4f} [{s['ci95'][0]:.3f}-{s['ci95'][1]:.3f}]{u}")

    info = summarise(model)
    n = min(512, len(Xte))
    model.predict(Xte[:32], verbose=0)                    # warm up
    t0 = time.time()
    model.predict(Xte[:n], batch_size=1, verbose=0)
    host_ms = (time.time() - t0) / n * 1000

    rec_out = {
        "evaluated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "threshold_rule": f"lowest threshold with validation FA rate <= {TARGET_FA_RATE}",
        "threshold": thr,
        "selection": {k: sw[k] for k in ("chosen", "best_f1", "rule_met")},
        "sweep_curve": sw["curve"],
        "architecture": info,
        "host_ms_per_inference": round(host_ms, 2),
        "results": results,
        "what_this_does_not_prove": [
            "These are clip metrics on centred 1.0 s windows, not streaming detection.",
            "False accepts per hour require continuous audio - see streaming_eval.py.",
            "Real-positive recall rests on a small number of distinct utterances from "
            "ONE speaker; the confidence interval, not the point estimate, is the "
            "honest summary.",
            "No result here is speaker-independent.",
        ],
    }
    (OUT / "evaluation_clip.json").write_text(json.dumps(rec_out, indent=2) + "\n",
                                              encoding="utf-8")
    print(f"\n{'=' * 78}")
    print(f"host inference {host_ms:.2f} ms/clip (batch=1)   "
          f"params {info['params']:,}   MACs {info['macs_per_inference']:,}")
    print(f"wrote {OUT / 'evaluation_clip.json'}")
    print("\nNOTE: clip metrics only. Streaming detection and FA/hour are measured")
    print("by training/streaming_eval.py and are the numbers that describe the device.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
