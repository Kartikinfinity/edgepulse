#!/usr/bin/env python3
"""Build the Takshila demo dataset. Deterministic and reproducible.

    python tools/build_dataset.py --smoke        # ~2 min sanity build
    python tools/build_dataset.py                # full build
    python tools/build_dataset.py --out data/dataset_v2

The build FAILS on any leakage. That is deliberate: a leaking dataset produces
a number that looks good and means nothing.

Nothing here trains a model.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.dataset_factory import build as B          # noqa: E402
from tools.dataset_factory import leakage, report, tts  # noqa: E402
from tools.dataset_factory.config import (DATASET_VERSION, KEYWORD, MASTER_SEED,  # noqa: E402
                                          OUT_DIR, SPEECH_COMMANDS, TARGETS,
                                          VOICES_DIR)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--smoke", action="store_true",
                    help="tiny build to validate the pipeline end to end")
    ap.add_argument("--force", action="store_true", help="overwrite an existing dataset")
    args = ap.parse_args()

    out: Path = args.out
    limit = 60 if args.smoke else None

    def log(msg: str) -> None:
        print(msg, flush=True)

    t0 = time.time()
    log("=" * 78)
    log(f"DATASET FACTORY — {DATASET_VERSION}   keyword='{KEYWORD}'   seed={MASTER_SEED}")
    log("=" * 78)

    # ---- preflight --------------------------------------------------------
    models = tts.available_models()
    log(f"TTS voice models      : {len(models)}")
    if not models:
        log("  ERROR: no Piper voices in " + str(VOICES_DIR))
        log("  Run the voice download step first (see DATASET_FACTORY.md).")
        return 2
    nvoices = sum(min(tts.voice_speaker_count(m), 10_000) for m in models)
    log(f"distinct TTS voices   : ~{nvoices}")
    log(f"Speech Commands       : {'FOUND' if SPEECH_COMMANDS.is_dir() else 'MISSING'} "
        f"({SPEECH_COMMANDS})")
    log(f"output                : {out}")
    if args.smoke:
        log("MODE                  : SMOKE (tiny)")
    log("")

    if out.exists() and any(out.iterdir()):
        if not args.force:
            log(f"ERROR: {out} exists and is not empty. Use --force to rebuild.")
            return 2
        log(f"removing existing {out}")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    noise_pool, noise_names = B.load_noise_pool()
    log(f"noise/background pool : {len(noise_names)} sources "
        f"({', '.join(noise_names[:4])}{'...' if len(noise_names) > 4 else ''})")
    log("")

    rows: list = []

    log("[1/5] real INMP441 keyword recordings (train + held-out test session)")
    real_kept, real_rej = B.gen_real_positives(rows, noise_pool, log)
    log(f"      {real_kept} usable recordings, {real_rej} rejected on duration/QC")
    log("")

    log("[2/5] TTS positives")
    ts = time.time()
    made, rej, parts = B.gen_tts_positives(rows, noise_pool, limit, log)
    log(f"      {made} positives, {parts} partial-keyword negatives, "
        f"{rej} rejected (outside the admissible duration)  [{time.time()-ts:.0f}s]")
    log("")

    log("[3/5] TTS phonetic hard negatives")
    ts = time.time()
    nneg = B.gen_hard_negatives(rows, noise_pool, limit, log)
    log(f"      {nneg} confusables  [{time.time()-ts:.0f}s]")
    log("")

    log("[4/5] real human speech negatives (Speech Commands)")
    nsc = B.gen_speech_negatives(rows, noise_pool, (limit * 4 if limit else None), log)
    log(f"      {nsc} clips")
    log("")

    log("[5/5] background + silence")
    nbg, nsi = B.gen_background_silence(rows, noise_pool, log)
    log(f"      {nbg} background, {nsi} silence")
    log("")

    log(f"writing {len(rows):,} clips ...")
    manifest = B.write_all(rows, out, log)
    log("")

    log("checking leakage ...")
    fails, warns, stats = leakage.check(manifest)

    elapsed = time.time() - t0
    rep = report.build_report(manifest, stats, fails, elapsed, warns)
    print(rep)

    (out / "DATASET_REPORT.txt").write_text(rep + "\n", encoding="utf-8")
    (out / "build_config.json").write_text(json.dumps({
        "dataset_version": DATASET_VERSION,
        "keyword": KEYWORD,
        "master_seed": MASTER_SEED,
        "smoke": args.smoke,
        "targets": TARGETS,
        "voice_models": models,
        "distinct_tts_voices": nvoices,
        "speech_commands_present": SPEECH_COMMANDS.is_dir(),
        "clips": len(manifest),
        "leakage_pass": not fails,
        "provisional": bool(warns),
        "warnings": warns,
        "build_seconds": round(elapsed, 1),
    }, indent=2) + "\n", encoding="utf-8")

    # Publish provenance to the TRACKED dataset_manifest/ directory. The audio
    # itself stays out of git; these files plus config.py are what make the
    # dataset reproducible from a fresh clone.
    prov = Path(__file__).resolve().parents[1] / "dataset_manifest"
    prov.mkdir(parents=True, exist_ok=True)
    (prov / "DATASET_REPORT.txt").write_text(rep + "\n", encoding="utf-8")
    shutil.copy2(out / "build_config.json", prov / "build_config.json")
    import gzip
    for split in ("train", "validation", "test"):
        src = out / "manifests" / f"{split}.csv"
        if src.is_file():
            with src.open("rb") as fi, gzip.open(prov / f"{split}.csv.gz", "wb") as fo:
                shutil.copyfileobj(fi, fo)
    log("")
    log(f"wrote {out}/manifests/*.csv, DATASET_REPORT.txt, build_config.json")
    log(f"published provenance to dataset_manifest/ (tracked in git)")
    if fails:
        log("BUILD FAILED — leakage detected. The dataset must not be used.")
        return 1
    log("BUILD OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
