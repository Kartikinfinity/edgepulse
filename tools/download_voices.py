#!/usr/bin/env python3
"""Download the Piper TTS voice models the dataset factory needs (~670 MB).

    python tools/download_voices.py

Voices are the diversity axis of the positive class: the multi-speaker models
below carry ~1,090 distinct voices between them, including L2-ARCTIC
(non-native English, our target population) and Indic voices that render the
ksha conjunct in "Takshila" natively. See docs/DATASET_RESEARCH.md 5.

Models are MIT-licensed; the Piper engine itself is GPL-3.0. Both are recorded
per clip in the dataset manifest.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dataset_factory.config import VOICE_MODELS, VOICES_DIR  # noqa: E402

RAW = "https://huggingface.co/rhasspy/piper-voices/raw/main/"
RESOLVE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"


def main() -> int:
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        index = json.loads(urllib.request.urlopen(RAW + "voices.json", timeout=60).read())
    except Exception as exc:
        print(f"ERROR: could not fetch the voice index: {exc}")
        return 2

    total = 0
    for name in VOICE_MODELS:
        if name not in index:
            print(f"  MISSING from index: {name}")
            continue
        for rel in index[name]["files"]:
            if not (rel.endswith(".onnx") or rel.endswith(".onnx.json")):
                continue
            dst = VOICES_DIR / Path(rel).name
            if dst.exists() and dst.stat().st_size > 1000:
                print(f"  have {dst.name}")
                continue
            t0 = time.time()
            try:
                urllib.request.urlretrieve(RESOLVE + rel, dst)
                mb = dst.stat().st_size / 1e6
                total += mb
                print(f"  got  {dst.name:<42} {mb:6.1f} MB  {time.time()-t0:.0f}s", flush=True)
            except Exception as exc:
                print(f"  FAIL {rel}: {exc}")
                return 1
    print(f"\n{total:.0f} MB downloaded into {VOICES_DIR}")
    print("next: python tools/build_dataset.py --force")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
