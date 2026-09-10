#!/usr/bin/env python3
"""Train the baseline Takshila KWS model.

    python training/train.py
    python training/train.py --epochs 30 --keyword-boost 0.7

Trains ONE architecture (DS-CNN, see training/model.py) on the built dataset,
using the same feature pipeline the firmware will run. Writes the model,
normalisation statistics and a training record to artifacts/model/.

This script does not choose a threshold. Threshold selection happens in
training/evaluate.py, on the VALIDATION split only.
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
from training.dataset import class_weights, load_split  # noqa: E402
from training.model import CLASS_NAMES, build_dscnn, summarise  # noqa: E402

OUT = ARTIFACTS_DIR / "model"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=DATASET_ROOT)
    ap.add_argument("--out", type=Path, default=OUT,
                    help="model directory; use a fresh one to keep an "
                         "earlier model intact for comparison")
    ap.add_argument("--label", default="",
                    help="short name recorded in training_record.json")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--channels", type=int, default=48)
    ap.add_argument("--blocks", type=int, default=3)
    ap.add_argument("--keyword-boost", type=float, default=1.0,
                    help="<1 down-weights the keyword class, trading recall for "
                         "fewer false accepts")
    ap.add_argument("--seed", type=int, default=20260910)
    args = ap.parse_args()
    out_dir: Path = args.out

    import tensorflow as tf
    tf.keras.utils.set_random_seed(args.seed)

    print("=" * 74)
    print("TRAINING BASELINE KWS MODEL — Takshila")
    print("=" * 74)
    print("feature pipeline:")
    for k, v in F.describe().items():
        print(f"  {k:<26} {v}")
    print()

    print("loading data")
    tr = load_split("train", args.dataset)
    va = load_split("validation", args.dataset)
    print()

    # Normalisation statistics come from TRAIN ONLY. Fitting them on the whole
    # set would leak validation/test distribution into the model input.
    mean, std = F.fit_normalisation(tr["X"][..., 0])
    # X is (N, 49, 13, 1); mean/std are (13,) so they need a trailing axis to
    # broadcast against the channel dimension.
    m4, s4 = mean[:, None], std[:, None]
    Xtr = F.apply_normalisation(tr["X"], m4, s4)
    Xva = F.apply_normalisation(va["X"], m4, s4)
    print("per-coefficient normalisation (train only)")
    print(f"  mean[0:4] {np.round(mean[:4], 3)}   std[0:4] {np.round(std[:4], 3)}")
    print()

    ytr, yva = tr["y"], va["y"]
    for name, y in (("train", ytr), ("validation", yva)):
        c = np.bincount(y, minlength=len(CLASS_NAMES))
        print(f"  {name:<11} " + "  ".join(f"{CLASS_NAMES[i]}={c[i]:,}"
                                           for i in range(len(CLASS_NAMES))))
    cw = class_weights(ytr, args.keyword_boost)
    print(f"  class weights: " + ", ".join(f"{CLASS_NAMES[i]}={cw[i]:.3f}" for i in cw))
    print()

    model = build_dscnn(len(CLASS_NAMES), args.channels, args.blocks)
    info = summarise(model)
    print("architecture")
    for k, v in info.items():
        print(f"  {k:<34} {v}")
    print()

    model.compile(
        optimizer=tf.keras.optimizers.Adam(args.lr),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    cbs = [
        tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=6,
                                         restore_best_weights=True, verbose=1),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5,
                                             patience=3, min_lr=1e-5, verbose=1),
    ]

    t0 = time.time()
    hist = model.fit(Xtr, ytr, validation_data=(Xva, yva),
                     epochs=args.epochs, batch_size=args.batch,
                     class_weight=cw, callbacks=cbs, verbose=2)
    train_s = time.time() - t0

    # host latency, measured not assumed
    warm = model.predict(Xva[:64], verbose=0)
    n = min(512, len(Xva))
    t0 = time.time()
    model.predict(Xva[:n], batch_size=1, verbose=0)
    host_ms = (time.time() - t0) / n * 1000

    model.save(out_dir / "kws_float.keras")
    np.savez(out_dir / "normalisation.npz", mean=mean, std=std)

    record = {
        "keyword": "Takshila",
        "label": args.label,
        "dataset": str(args.dataset),
        "trained_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": args.seed,
        "epochs_requested": args.epochs,
        "epochs_run": len(hist.history["loss"]),
        "batch": args.batch, "lr": args.lr,
        "keyword_boost": args.keyword_boost,
        "class_weights": {CLASS_NAMES[i]: cw[i] for i in cw},
        "architecture": info,
        "feature_pipeline": F.describe(),
        "normalisation": {"mean": mean.tolist(), "std": std.tolist()},
        "train_clips": int(len(ytr)), "validation_clips": int(len(yva)),
        "final_train_accuracy": float(hist.history["accuracy"][-1]),
        "final_val_accuracy": float(hist.history["val_accuracy"][-1]),
        "best_val_accuracy": float(max(hist.history["val_accuracy"])),
        "train_seconds": round(train_s, 1),
        "host_ms_per_inference": round(host_ms, 2),
        "history": {k: [float(x) for x in v] for k, v in hist.history.items()},
    }
    (out_dir / "training_record.json").write_text(json.dumps(record, indent=2) + "\n",
                                              encoding="utf-8")

    print()
    print("=" * 74)
    print(f"epochs run            {record['epochs_run']}")
    print(f"best val accuracy     {record['best_val_accuracy']:.4f}")
    print(f"train time            {train_s/60:.1f} min")
    print(f"host inference        {host_ms:.2f} ms/clip (batch=1)")
    print(f"params / MACs         {info['params']:,} / {info['macs_per_inference']:,}")
    print(f"saved                 {out_dir/'kws_float.keras'}")
    print("=" * 74)
    print("\nNOTE: accuracy here is a CLIP metric on a TTS-dominated validation")
    print("set. It is a training signal, not a result. The numbers that matter")
    print("come from training/evaluate.py, on real audio and a threshold sweep.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
