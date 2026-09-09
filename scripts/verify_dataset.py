#!/usr/bin/env python3
"""Verify this machine has the correct dataset, without the WAVs being in Git.

    python scripts/verify_dataset.py            # structure + counts + sampled hashes
    python scripts/verify_dataset.py --full     # every file hashed (slow, definitive)
    python scripts/verify_dataset.py --sample 500

Exit code 0 = the dataset matches dataset_manifest/manifest.json.
Anything else = do not train on this data until it is fixed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import DATASET_ROOT, MANIFEST_DIR  # noqa: E402

CHUNK = 1 << 20
OK, BAD = "  [ ok ]", "  [FAIL]"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="hash every file (slow)")
    ap.add_argument("--sample", type=int, default=200, help="files to spot-check (default 200)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    manifest_path = MANIFEST_DIR / "manifest.json"
    checksums_path = MANIFEST_DIR / "CHECKSUMS.sha256"
    failures: list[str] = []

    print("=" * 68)
    print("DATASET VERIFICATION")
    print("=" * 68)
    print(f"dataset root : {DATASET_ROOT}")
    print(f"manifest     : {manifest_path}")
    print()

    if not manifest_path.is_file() or not checksums_path.is_file():
        print(f"{BAD} dataset_manifest/ is incomplete - cannot verify.")
        return 2
    if not DATASET_ROOT.is_dir():
        print(f"{BAD} dataset root does not exist.")
        print("        See DATASET_SETUP.md, then set SIH_DATASET_ROOT in .env.")
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"expected version: {manifest['dataset_version']}  keyword={manifest['keyword']}")
    print()

    # ---- 1. structure -----------------------------------------------------
    print("1. Layout")
    for variant, vdata in manifest["variants"].items():
        vroot = DATASET_ROOT / variant
        if not vroot.is_dir():
            print(f"{BAD} missing variant directory: {variant}")
            failures.append(f"missing variant {variant}")
            continue
        for split in vdata["splits"]:
            for cls in manifest["variants"][variant]["splits"][split]["wav_counts"]:
                if not (vroot / split / cls).is_dir():
                    print(f"{BAD} missing {variant}/{split}/{cls}")
                    failures.append(f"missing dir {variant}/{split}/{cls}")
    if not failures:
        print(f"{OK} all variant/split/class directories present")
    print()

    # ---- 2. counts --------------------------------------------------------
    print("2. File counts and manifest rows")
    for variant, vdata in manifest["variants"].items():
        vroot = DATASET_ROOT / variant
        if not vroot.is_dir():
            continue
        for split, sdata in vdata["splits"].items():
            for cls, expected in sdata["wav_counts"].items():
                actual = len(list((vroot / split / cls).glob("*.wav")))
                if actual != expected:
                    print(f"{BAD} {variant}/{split}/{cls}: expected {expected}, found {actual}")
                    failures.append(f"count {variant}/{split}/{cls}")
            csv_path = vroot / "manifests" / f"{split}.csv"
            if csv_path.is_file():
                rows = max(0, sum(1 for _ in csv_path.open(encoding="utf-8")) - 1)
                if rows != sdata["manifest_rows"]:
                    print(f"{BAD} {variant}/manifests/{split}.csv: "
                          f"expected {sdata['manifest_rows']} rows, found {rows}")
                    failures.append(f"rows {variant}/{split}")
                actual_sha = sha256_file(csv_path)
                if sdata["manifest_sha256"] and actual_sha != sdata["manifest_sha256"]:
                    print(f"{BAD} {variant}/manifests/{split}.csv checksum mismatch")
                    failures.append(f"csv sha {variant}/{split}")
            else:
                print(f"{BAD} missing {variant}/manifests/{split}.csv")
                failures.append(f"missing csv {variant}/{split}")
        print(f"       {variant}: {vdata['wav_total']:,} wav / "
              f"{vdata['manifest_rows_total']:,} manifest rows expected")
    if not any(f.startswith(("count", "rows", "csv", "missing csv")) for f in failures):
        print(f"{OK} counts and manifest CSV checksums match")
    print()

    # ---- 3. checksums -----------------------------------------------------
    expected: dict[str, str] = {}
    for line in checksums_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, _, rel = line.partition("  ")
            expected[rel] = digest

    total_expected = manifest["totals"]["files"]
    if len(expected) != total_expected:
        print(f"{BAD} CHECKSUMS.sha256 lists {len(expected)} files, manifest says {total_expected}")
        failures.append("checksum file inconsistent")

    if args.full:
        print(f"3. Hashing all {len(expected):,} files (this takes a while)")
        targets = sorted(expected)
    else:
        n = min(args.sample, len(expected))
        rng = random.Random(args.seed)
        targets = rng.sample(sorted(expected), n)
        print(f"3. Spot-checking {n} of {len(expected):,} files (--full for all)")

    missing = mismatched = 0
    for i, rel in enumerate(targets, 1):
        path = DATASET_ROOT / rel
        if not path.is_file():
            missing += 1
            if missing <= 5:
                print(f"{BAD} missing file: {rel}")
            continue
        if sha256_file(path) != expected[rel]:
            mismatched += 1
            if mismatched <= 5:
                print(f"{BAD} checksum mismatch: {rel}")
        if args.full and i % 2000 == 0:
            print(f"       {i:,}/{len(targets):,}")

    if missing or mismatched:
        print(f"{BAD} {missing} missing, {mismatched} mismatched of {len(targets)} checked")
        failures.append("checksum mismatch")
    else:
        print(f"{OK} {len(targets)} files verified byte-identical")

    if args.full and not failures:
        # Recompute the single root hash - the strongest statement available.
        lines = [f"{expected[r]}  {r}" for r in sorted(expected)]
        root = hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()
        if root == manifest["root_sha256"]:
            print(f"{OK} root_sha256 matches: {root}")
        else:
            print(f"{BAD} root_sha256 mismatch")
            failures.append("root hash")
    print()

    print("=" * 68)
    if failures:
        print(f"RESULT: FAILED - {len(failures)} problem(s)")
        for f in dict.fromkeys(failures):
            print(f"  - {f}")
        print("\nSee DATASET_SETUP.md. Do not train on unverified data.")
        return 1
    print("RESULT: PASS - dataset matches the committed manifest")
    if not args.full:
        print("        (spot-check only; run --full before publishing any result)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
