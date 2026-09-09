"""Load the built dataset and turn it into 49x13 features, with caching.

Feature extraction runs the SAME `training.features` code the device mirrors, so
what the model trains on is what the firmware will compute. Caching is keyed on
the manifest content, so an edited dataset invalidates the cache automatically
rather than silently training on stale features.
"""

from __future__ import annotations

import csv
import hashlib
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import ARTIFACTS_DIR, DATASET_ROOT  # noqa: E402
from training import features as F  # noqa: E402
from training.model import CLASS_NAMES  # noqa: E402

CACHE_DIR = ARTIFACTS_DIR / "features"
TARGET_INDEX = {name: i for i, name in enumerate(CLASS_NAMES)}


def read_manifest(split: str, dataset: Path = DATASET_ROOT) -> list[dict]:
    p = dataset / "manifests" / f"{split}.csv"
    if not p.is_file():
        raise FileNotFoundError(f"missing manifest: {p}")
    with p.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _cache_key(rows: list[dict], split: str) -> str:
    h = hashlib.sha256()
    h.update(split.encode())
    h.update(str(F.describe()).encode())
    for r in rows:
        h.update(r["clip_id"].encode())
        h.update(r["sha256"].encode())
    return h.hexdigest()[:16]


def load_split(split: str, dataset: Path = DATASET_ROOT,
               use_cache: bool = True, log=print) -> dict:
    """Return dict with X (N,49,13,1) float32, y (N,) int, and the manifest rows."""
    rows = read_manifest(split, dataset)
    key = _cache_key(rows, split)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{split}_{key}.npz"

    if use_cache and cache.is_file():
        d = np.load(cache)
        log(f"  {split:<11} {len(rows):>6,} clips  (cached {cache.name})")
        return {"X": d["X"], "y": d["y"], "rows": rows}

    t0 = time.time()
    X = np.zeros((len(rows), F.N_FRAMES, F.N_MFCC), dtype=np.float32)
    y = np.zeros(len(rows), dtype=np.int64)
    import wave
    for i, r in enumerate(rows):
        path = dataset / r["filepath"]
        with wave.open(str(path), "rb") as w:
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        X[i] = F.clip_features(pcm)
        y[i] = TARGET_INDEX[r["model_target"]]
        if (i + 1) % 4000 == 0:
            log(f"    {split}: {i+1:,}/{len(rows):,}")
    X = X[..., None]
    np.savez_compressed(cache, X=X, y=y)
    log(f"  {split:<11} {len(rows):>6,} clips  extracted in {time.time()-t0:.0f}s")
    return {"X": X, "y": y, "rows": rows}


def subset_mask(rows: list[dict], **conditions) -> np.ndarray:
    """Boolean mask over rows. Each condition is field -> value or (values...).

        subset_mask(rows, **{"class": "positive", "synthetic": "false"})
    """
    m = np.ones(len(rows), dtype=bool)
    for field, want in conditions.items():
        if isinstance(want, (list, tuple, set)):
            m &= np.array([r.get(field) in want for r in rows])
        else:
            m &= np.array([r.get(field) == want for r in rows])
    return m


def class_weights(y: np.ndarray, keyword_boost: float = 1.0) -> dict[int, float]:
    """Inverse-frequency weights, with an explicit knob on the keyword class.

    Raising the NEGATIVE weight (i.e. keyword_boost < 1) is the documented lever
    for cutting false accepts. It is exposed rather than baked in so the
    trade-off is made deliberately and recorded.
    """
    counts = np.bincount(y, minlength=len(CLASS_NAMES)).astype(np.float64)
    counts[counts == 0] = 1.0
    w = counts.sum() / (len(counts) * counts)
    w[TARGET_INDEX["keyword"]] *= keyword_boost
    return {i: float(v) for i, v in enumerate(w)}
