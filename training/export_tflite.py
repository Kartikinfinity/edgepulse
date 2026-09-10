#!/usr/bin/env python3
"""Quantise the trained model to int8 TFLite and prove the quantisation is safe.

    python training/export_tflite.py

Exporting is the easy half. The half that matters is showing that the int8 model
still makes the same decisions as the float model it came from - because every
number measured by evaluate.py and streaming_eval.py was measured on the FLOAT
model, and those numbers only carry over to the device if quantisation did not
move the scores.

So this script exports, then re-scores the whole test split through the actual
TFLite interpreter and reports the disagreement. It writes the tensor shapes and
quantisation parameters the firmware needs, and it fails loudly if the int8
model diverges enough to invalidate the float results.
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
from training.dataset import load_split  # noqa: E402
from training.model import KEYWORD_IDX  # noqa: E402

OUT = ARTIFACTS_DIR / "model"

# Pre-declared pass bar. Checked after export, not adjusted to fit the result.
MAX_SCORE_DRIFT = 0.05         # max |P_float - P_int8| over the test split
MIN_CORRELATION = 0.99
MAX_DECISION_FLIPS = 0.01      # <=1% of clips may cross the threshold


def representative_dataset(Xtr: np.ndarray, n: int = 500, seed: int = 20260910):
    """Calibration samples. Drawn from TRAIN only - using validation or test
    audio to calibrate would leak those distributions into the deployed model."""
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(Xtr), size=min(n, len(Xtr)), replace=False)

    def gen():
        for i in idx:
            yield [Xtr[i:i + 1].astype(np.float32)]
    return gen


def tflite_scores(path: Path, X: np.ndarray) -> np.ndarray:
    """Run every clip through the real interpreter, one at a time, exactly as
    the device will. Batch inference would not exercise the same code path."""
    import tensorflow as tf
    interp = tf.lite.Interpreter(model_path=str(path))
    interp.allocate_tensors()
    inp, outp = interp.get_input_details()[0], interp.get_output_details()[0]
    i_scale, i_zero = inp["quantization"]
    o_scale, o_zero = outp["quantization"]
    out = np.zeros(len(X), dtype=np.float64)
    for i in range(len(X)):
        x = X[i:i + 1]
        if inp["dtype"] == np.int8:
            q = np.clip(np.round(x / i_scale + i_zero), -128, 127).astype(np.int8)
        else:
            q = x.astype(inp["dtype"])
        interp.set_tensor(inp["index"], q)
        interp.invoke()
        y = interp.get_tensor(outp["index"])[0]
        if outp["dtype"] == np.int8:
            y = (y.astype(np.float64) - o_zero) * o_scale
        out[i] = y[KEYWORD_IDX]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=DATASET_ROOT)
    ap.add_argument("--model", type=Path, default=OUT / "kws_float.keras")
    ap.add_argument("--out", type=Path, default=None,
                    help="output directory (default: the model's own)")
    args = ap.parse_args()
    # Artifacts belong beside the model they came from; a fixed OUT would
    # overwrite model-1's export with model-2's.
    out_dir = args.out or args.model.parent

    import tensorflow as tf
    model = tf.keras.models.load_model(args.model)
    norm = np.load(out_dir / "normalisation.npz")
    m4, s4 = norm["mean"][:, None], norm["std"][:, None]

    print("=" * 78)
    print("TFLITE INT8 EXPORT + QUANTISATION PARITY")
    print("=" * 78)

    tr = load_split("train", args.dataset)
    te = load_split("test", args.dataset)
    Xtr = F.apply_normalisation(tr["X"], m4, s4)
    Xte = F.apply_normalisation(te["X"], m4, s4)

    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    conv.representative_dataset = representative_dataset(Xtr)
    # Full integer: TFLM with ESP-NN has int8 kernels; a float fallback op would
    # silently fall off the accelerated path and blow the latency budget.
    conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    conv.inference_input_type = tf.int8
    conv.inference_output_type = tf.int8
    t0 = time.time()
    blob = conv.convert()
    path = out_dir / "kws_int8.tflite"
    path.write_bytes(blob)
    print(f"\nexported  {path}  ({len(blob):,} bytes, {time.time() - t0:.0f}s)")

    interp = tf.lite.Interpreter(model_path=str(path))
    interp.allocate_tensors()
    inp, outp = interp.get_input_details()[0], interp.get_output_details()[0]
    print("\ntensors the firmware must match:")
    for tag, d in (("input", inp), ("output", outp)):
        s, z = d["quantization"]
        print(f"  {tag:<7} shape {list(d['shape'])}  dtype {np.dtype(d['dtype']).name}"
              f"  scale {s:.8f}  zero_point {z}")

    ops = {}
    for d in interp._get_ops_details() if hasattr(interp, "_get_ops_details") else []:
        ops[d["op_name"]] = ops.get(d["op_name"], 0) + 1
    if ops:
        print("  ops: " + ", ".join(f"{k} x{v}" for k, v in sorted(ops.items())))

    # ---- does int8 still decide the same things? --------------------------
    print(f"\nre-scoring {len(Xte):,} test clips through the interpreter")
    t0 = time.time()
    p_int8 = tflite_scores(path, Xte)
    tfl_ms = (time.time() - t0) / len(Xte) * 1000
    p_float = model.predict(Xte, batch_size=256, verbose=0)[:, KEYWORD_IDX]

    drift = float(np.abs(p_float - p_int8).max())
    corr = float(np.corrcoef(p_float, p_int8)[0, 1])
    clip_eval_path = out_dir / "evaluation_clip.json"
    thr = json.loads(clip_eval_path.read_text(encoding="utf-8"))["threshold"] \
        if clip_eval_path.is_file() else 0.5
    flips = float(((p_float >= thr) != (p_int8 >= thr)).mean())

    print(f"  max |P_float - P_int8|   {drift:.6f}   (bar < {MAX_SCORE_DRIFT})")
    print(f"  correlation              {corr:.8f}   (bar > {MIN_CORRELATION})")
    print(f"  decision flips at {thr:.3f}  {flips:.4%}  "
          f"({int(flips * len(Xte))} clips, bar < {MAX_DECISION_FLIPS:.0%})")
    print(f"  host interpreter         {tfl_ms:.2f} ms/clip (single-sample invoke)")

    passed = (drift < MAX_SCORE_DRIFT and corr > MIN_CORRELATION
              and flips < MAX_DECISION_FLIPS)

    rec = {
        "exported_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file": str(path.name), "bytes": len(blob),
        "input": {"shape": [int(v) for v in inp["shape"]],
                  "dtype": np.dtype(inp["dtype"]).name,
                  "scale": float(inp["quantization"][0]),
                  "zero_point": int(inp["quantization"][1])},
        "output": {"shape": [int(v) for v in outp["shape"]],
                   "dtype": np.dtype(outp["dtype"]).name,
                   "scale": float(outp["quantization"][0]),
                   "zero_point": int(outp["quantization"][1])},
        "ops": ops,
        "calibration": "500 TRAIN clips, seeded",
        "parity": {"max_score_drift": drift, "correlation": corr,
                   "decision_flip_rate": flips, "threshold": thr,
                   "bars": {"max_score_drift": MAX_SCORE_DRIFT,
                            "min_correlation": MIN_CORRELATION,
                            "max_decision_flips": MAX_DECISION_FLIPS},
                   "passed": passed},
        "host_tflite_ms_per_inference": round(tfl_ms, 2),
        "what_this_does_not_prove": [
            "This is the TFLite interpreter on the host, not TFLM+ESP-NN on the "
            "ESP32-S3. Kernel implementations differ; on-device output must be "
            "compared against these same clips before any device claim.",
            "Host ms/clip says nothing about device latency.",
            "Quantisation parity is not accuracy - it only shows int8 agrees "
            "with the float model the accuracy was measured on.",
        ],
    }
    (out_dir / "export_tflite.json").write_text(json.dumps(rec, indent=2) + "\n",
                                            encoding="utf-8")
    print(f"\nwrote {out_dir / 'export_tflite.json'}")
    print("=" * 78)
    print("QUANTISATION PARITY: " + ("PASS" if passed else "FAIL"))
    if not passed:
        print("The int8 model does not agree with the float model closely enough.")
        print("Every float number measured so far is therefore NOT transferable")
        print("to the device. Fix this before deploying.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
