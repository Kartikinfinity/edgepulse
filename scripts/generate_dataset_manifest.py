#!/usr/bin/env python3
"""Generate the committed dataset fingerprint.

The 21,267 WAV files are deliberately NOT in Git. This script produces two
small files that let any other machine prove it has byte-identical data:

    dataset_manifest/manifest.json      counts, structure, aggregate hashes
    dataset_manifest/CHECKSUMS.sha256   one SHA-256 per file, sorted

Run it only when the dataset itself legitimately changes. To *check* a dataset,
use scripts/verify_dataset.py instead.

    python scripts/generate_dataset_manifest.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import CLASSES, DATASET_ROOT, MANIFEST_DIR, SPLITS, VARIANTS  # noqa: E402

DATASET_VERSION = "solvani_kws_release-1.0"
CHUNK = 1 << 20


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not DATASET_ROOT.is_dir():
        print(f"ERROR: dataset root not found: {DATASET_ROOT}", file=sys.stderr)
        print("Set SIH_DATASET_ROOT in .env, or see DATASET_SETUP.md.", file=sys.stderr)
        return 2

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()

    # --- every file under the dataset root, relative + POSIX for portability --
    all_files = sorted(
        (p for p in DATASET_ROOT.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(DATASET_ROOT).as_posix(),
    )
    print(f"hashing {len(all_files):,} files under {DATASET_ROOT} ...", flush=True)

    lines: list[str] = []
    per_file: dict[str, str] = {}
    total_bytes = 0
    for i, path in enumerate(all_files, 1):
        rel = path.relative_to(DATASET_ROOT).as_posix()
        digest = sha256_file(path)
        per_file[rel] = digest
        total_bytes += path.stat().st_size
        lines.append(f"{digest}  {rel}")
        if i % 2000 == 0:
            print(f"  {i:,}/{len(all_files):,}", flush=True)

    checksums_path = MANIFEST_DIR / "CHECKSUMS.sha256"
    checksums_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # --- structure and counts -------------------------------------------------
    variants: dict[str, dict] = {}
    for variant in VARIANTS:
        vroot = DATASET_ROOT / variant
        if not vroot.is_dir():
            continue
        splits: dict[str, dict] = {}
        for split in SPLITS:
            classes = {}
            for cls in CLASSES:
                cdir = vroot / split / cls
                classes[cls] = len(list(cdir.glob("*.wav"))) if cdir.is_dir() else 0
            csv_path = vroot / "manifests" / f"{split}.csv"
            rows = 0
            csv_sha = None
            if csv_path.is_file():
                # header line excluded from the row count
                rows = max(0, sum(1 for _ in csv_path.open(encoding="utf-8")) - 1)
                csv_sha = per_file[csv_path.relative_to(DATASET_ROOT).as_posix()]
            splits[split] = {
                "wav_counts": classes,
                "wav_total": sum(classes.values()),
                "manifest_rows": rows,
                "manifest_sha256": csv_sha,
            }
        variants[variant] = {
            "splits": splits,
            "wav_total": sum(s["wav_total"] for s in splits.values()),
            "manifest_rows_total": sum(s["manifest_rows"] for s in splits.values()),
        }

    wav_files = [r for r in per_file if r.endswith(".wav")]

    # Root hash: SHA-256 over the sorted "<sha>  <relpath>" lines. Any change to
    # any file, name or ordering changes this single value.
    root_hash = hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()

    manifest = {
        "dataset_version": DATASET_VERSION,
        "keyword": "solvani",
        "generated_by": "scripts/generate_dataset_manifest.py",
        "expected_dataset_root": "data/solvani_kws_release",
        "expected_dataset_root_note": (
            "Relative to the repository root. Override with SIH_DATASET_ROOT in .env "
            "if the dataset lives elsewhere on this machine."
        ),
        "audio_format": {
            "sample_rate_hz": 16000,
            "channels": 1,
            "sample_format": "PCM signed 16-bit little-endian",
            "frames_per_clip": 16000,
            "duration_s": 1.0,
        },
        "layout": [
            "<root>/README.md",
            "<root>/<variant>/README.md",
            "<root>/<variant>/REPORT.md",
            "<root>/<variant>/manifests/{train,validation,test}.csv",
            "<root>/<variant>/{train,validation,test}/{positive,negative,background}/*.wav",
        ],
        "variants": variants,
        "totals": {
            "files": len(all_files),
            "wav_files": len(wav_files),
            "bytes": total_bytes,
        },
        "root_sha256": root_hash,
        "root_sha256_note": (
            "SHA-256 over the exact contents of CHECKSUMS.sha256 (sorted "
            "'<sha256>  <relative/posix/path>' lines). One value that changes if any "
            "file's content, name or presence changes. It therefore equals "
            "checksums_file_sha256 by construction - that is intended, not a bug."
        ),
        "checksums_file": "dataset_manifest/CHECKSUMS.sha256",
        "checksums_file_sha256": sha256_file(checksums_path),
    }

    manifest_path = MANIFEST_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    elapsed = time.time() - started
    print(f"\nwrote {manifest_path}")
    print(f"wrote {checksums_path}")
    print(f"  files      : {len(all_files):,}  ({len(wav_files):,} wav)")
    print(f"  bytes      : {total_bytes:,}")
    print(f"  root sha256: {root_hash}")
    print(f"  elapsed    : {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
