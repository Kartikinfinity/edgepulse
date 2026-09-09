#!/usr/bin/env python3
"""Project health check - what state is this checkout actually in?

    python scripts/health_check.py

Answers the questions a new session asks first: is the tree clean, which build
phases have produced anything, what is blocked, and is there room to work.
Reports state; it changes nothing.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

# The documents use emoji status markers. A Windows console defaults to cp1252
# and raises UnicodeEncodeError on them, so keep every line we print ASCII-safe.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass


def ascii_safe(text: str) -> str:
    """Drop characters the console cannot encode, collapsing the gaps."""
    cleaned = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s{2,}", " ", cleaned).strip()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import (  # noqa: E402
    ARTIFACTS_DIR,
    DATASET_ROOT,
    EXPERIMENTS_DIR,
    FIRMWARE_DIR,
    PROJECT_ROOT,
    SERVER_DIR,
    TRAINING_DIR,
    UI_DIR,
)

OK, WARN, BAD, PEND = "[ ok ]", "[warn]", "[FAIL]", "[    ]"


def git(*args: str) -> str:
    exe = shutil.which("git")
    if not exe:
        return ""
    try:
        r = subprocess.run([exe, "-C", str(PROJECT_ROOT), *args],
                           capture_output=True, text=True, timeout=60)
        return r.stdout.strip()
    except Exception:
        return ""


def has_code(d: Path, *patterns: str) -> int:
    if not d.is_dir():
        return 0
    return sum(len(list(d.rglob(p))) for p in patterns)


def main() -> int:
    print("=" * 68)
    print("SIH KWS - PROJECT HEALTH CHECK")
    print("=" * 68)
    print(f"root: {PROJECT_ROOT}")
    print()

    # --- Git ---------------------------------------------------------------
    print("GIT")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    head = git("rev-parse", "--short", "HEAD")
    count = git("rev-list", "--count", "HEAD")
    status = git("status", "--short")
    remotes = git("remote", "-v")
    print(f"  branch  : {branch or '(unknown)'}")
    print(f"  HEAD    : {head or '(unknown)'}  ({count or '?'} commits)")
    print(f"  {OK if not status else WARN} working tree: "
          f"{'clean' if not status else str(len(status.splitlines())) + ' uncommitted change(s)'}")
    if status:
        for line in status.splitlines()[:10]:
            print(f"        {line}")
    print(f"  {OK if remotes else WARN} remote: {remotes.splitlines()[0] if remotes else 'none configured'}")
    print()

    # --- Build phase progress ---------------------------------------------
    print("BUILD PHASE PROGRESS  (see BUILD_PLAN.md)")
    venv = any((PROJECT_ROOT / v).is_dir() for v in (".venv", "venv", "env"))
    pio_ini = (FIRMWARE_DIR / "platformio.ini").is_file()
    fw_src = has_code(FIRMWARE_DIR / "src", "*.cpp", "*.c", "*.h")
    train_code = has_code(TRAINING_DIR, "*.py")
    server_code = has_code(SERVER_DIR, "*.py")
    ui_code = has_code(UI_DIR, "*.html", "*.js", "*.css")
    artifacts = has_code(ARTIFACTS_DIR, "*.npz", "*.tflite", "*.keras", "*.h5")
    experiments = len(list(EXPERIMENTS_DIR.glob("*.md"))) if EXPERIMENTS_DIR.is_dir() else 0

    rows = [
        ("A1", "Python venv", venv),
        ("A2", "PlatformIO config", pio_ini),
        ("A3-A6", "firmware source / bring-up", bool(fw_src)),
        ("B", "feature pipeline (training/)", bool(train_code)),
        ("C", "streaming eval harness", bool(train_code)),
        ("E", "model artifacts", bool(artifacts)),
        ("G", "ASR server (server/)", bool(server_code)),
        ("H", "demo UI (ui/)", bool(ui_code)),
        ("--", "experiment records", experiments > 0),
    ]
    for tag, label, done in rows:
        print(f"  {OK if done else PEND} {tag:<6} {label}")
    print(f"\n  experiment records in docs/experiments: {experiments}")
    print(f"  artifact files                        : {artifacts}")
    print()

    # --- Dataset -----------------------------------------------------------
    print("DATASET")
    if DATASET_ROOT.is_dir():
        n = sum(1 for _ in DATASET_ROOT.rglob("*.wav"))
        print(f"  {OK} {DATASET_ROOT}")
        print(f"       {n:,} wav files  (expect 21,267 - run scripts/verify_dataset.py)")
    else:
        print(f"  {BAD} not found: {DATASET_ROOT}   see DATASET_SETUP.md")
    print()

    # --- Blockers, read straight out of STATUS.md --------------------------
    print("BLOCKERS  (parsed from STATUS.md)")
    status_md = PROJECT_ROOT / "STATUS.md"
    if status_md.is_file():
        text = status_md.read_text(encoding="utf-8")
        found = re.findall(r"^###\s+(.*?B-\d+.*)$", text, flags=re.MULTILINE)
        if found:
            for line in found:
                clean = ascii_safe(line.replace("**", ""))
                open_marker = "RESOLVED" not in clean.upper()
                print(f"  {WARN if open_marker else OK} {clean}")
        else:
            print(f"  {WARN} no B-n headings found")
    else:
        print(f"  {BAD} STATUS.md missing")
    print()

    # --- Disk --------------------------------------------------------------
    print("DISK")
    try:
        usage = shutil.disk_usage(PROJECT_ROOT)
        free_gb = usage.free / (1024 ** 3)
        marker = OK if free_gb >= 15 else (WARN if free_gb >= 5 else BAD)
        print(f"  {marker} {free_gb:,.1f} GB free on the project volume "
              f"({usage.total / (1024 ** 3):,.0f} GB total)")
        if free_gb < 15:
            print("        The project needs ~12 GB over its lifetime (STORAGE_AUDIT.md 7).")
    except Exception as exc:
        print(f"  {WARN} could not read disk usage: {exc}")
    print()

    print("=" * 68)
    print("Health check is informational; it never modifies the project.")
    print("Next step is always the one named in CURRENT_HANDOFF.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
