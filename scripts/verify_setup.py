#!/usr/bin/env python3
"""Verify a development machine is ready to work on this project.

    python scripts/verify_setup.py

Checks Python, required packages, Git, PlatformIO, the project layout and the
dataset. Uses only the standard library itself, so it runs before anything is
installed and tells you what is missing.

Exit code 0 = every REQUIRED check passed.
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import (  # noqa: E402
    DATASET_ROOT,
    ENV_FILE,
    PROJECT_ROOT,
    RECORDINGS_ROOT,
    UPLOAD_PORT,
)

OK, WARN, BAD = "[ ok ]", "[warn]", "[FAIL]"
MIN_PYTHON = (3, 10)

# (import name, pip name, required?, note)
PACKAGES = [
    ("numpy", "numpy", True, "arrays, everywhere"),
    ("scipy", "scipy", True, "spectrogram / signal analysis"),
    ("soundfile", "soundfile", True, "WAV I/O for the feature pipeline (Phase B)"),
    ("tensorflow", "tensorflow", True, "training + TFLite int8 export (Phases E)"),
    ("librosa", "librosa", False, "convenience DSP; the pipeline does not depend on it"),
    ("matplotlib", "matplotlib", False, "analysis figures"),
    ("torch", "torch", False, "not used by the TFLM architecture; PS-allowed alternative"),
    ("pytest", "pytest", False, "test runner (requirements-dev.txt)"),
]

EXPECTED_DIRS = ["config", "scripts", "tools", "training", "firmware", "server", "ui", "docs"]
EXPECTED_DOCS = [
    "CLAUDE.md", "README.md", "STATUS.md", "BUILD_PLAN.md", "ARCHITECTURE.md",
    "DATASET.md", "HARDWARE.md", "DECISIONS.md", "BUILD_LOG.md",
    "PROJECT_STATE.md", "CURRENT_HANDOFF.md", "ENVIRONMENT_SETUP.md",
    "EXPERIMENT_STATE.md",
]


def run(cmd: list[str]) -> str | None:
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        out = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=90)
        return (out.stdout + out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else ""
    except Exception:
        return None


def main() -> int:
    required_failures: list[str] = []
    warnings: list[str] = []

    print("=" * 68)
    print("SIH KWS - SETUP VERIFICATION")
    print("=" * 68)
    print(f"project root : {PROJECT_ROOT}")
    print(f"platform     : {sys.platform}")
    print()

    # 1. Python -------------------------------------------------------------
    print("1. Python  [REQUIRED]")
    v = sys.version_info
    if (v.major, v.minor) >= MIN_PYTHON:
        print(f"  {OK} Python {v.major}.{v.minor}.{v.micro}")
    else:
        print(f"  {BAD} Python {v.major}.{v.minor} - need >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")
        required_failures.append("python version")
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if in_venv:
        print(f"  {OK} running inside a virtual environment")
    else:
        print(f"  {WARN} not in a virtual environment - see ENVIRONMENT_SETUP.md")
        warnings.append("no venv")
    print()

    # 2. Packages -----------------------------------------------------------
    print("2. Python packages")
    for mod, pip_name, required, note in PACKAGES:
        tag = "[REQUIRED]" if required else "[optional]"
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "?")
            print(f"  {OK} {mod:<12} {ver:<12} {tag} {note}")
        except Exception:
            if required:
                print(f"  {BAD} {mod:<12} {'MISSING':<12} {tag} pip install {pip_name}")
                required_failures.append(f"package {mod}")
            else:
                print(f"  {WARN} {mod:<12} {'absent':<12} {tag} {note}")
                warnings.append(f"optional package {mod}")
    print()

    # 3. External tools -----------------------------------------------------
    print("3. External tools")
    git = run(["git", "--version"])
    if git:
        print(f"  {OK} {git}  [REQUIRED]")
    else:
        print(f"  {BAD} git not found  [REQUIRED]")
        required_failures.append("git")

    pio = run(["pio", "--version"]) or run(["platformio", "--version"])
    if pio:
        print(f"  {OK} {pio}  [REQUIRED for firmware only]")
    else:
        print(f"  {WARN} PlatformIO not found - needed only for Phases A2/F")
        warnings.append("platformio")
    print()

    # 4. Project layout -----------------------------------------------------
    print("4. Project layout  [REQUIRED]")
    missing_dirs = [d for d in EXPECTED_DIRS if not (PROJECT_ROOT / d).is_dir()]
    missing_docs = [d for d in EXPECTED_DOCS if not (PROJECT_ROOT / d).is_file()]
    if missing_dirs:
        print(f"  {BAD} missing directories: {', '.join(missing_dirs)}")
        required_failures.append("project dirs")
    else:
        print(f"  {OK} all {len(EXPECTED_DIRS)} expected directories present")
    if missing_docs:
        print(f"  {BAD} missing documents: {', '.join(missing_docs)}")
        required_failures.append("project docs")
    else:
        print(f"  {OK} all {len(EXPECTED_DOCS)} core documents present")
    print()

    # 5. Configuration ------------------------------------------------------
    print("5. Configuration")
    if ENV_FILE.is_file():
        print(f"  {OK} .env present ({ENV_FILE})")
    else:
        print(f"  {WARN} no .env - defaults in use. Copy .env.example to .env to customise.")
        warnings.append("no .env")
    print(f"  {OK if UPLOAD_PORT else WARN} serial port: {UPLOAD_PORT or 'auto-detect (SIH_UPLOAD_PORT unset)'}")
    print()

    # 6. Dataset ------------------------------------------------------------
    # There is deliberately NO approved dataset: the previous corpus was deprecated
    # (DECISIONS.md D-010) and building a new one is the current task. Its absence is
    # therefore reported as expected state, NOT as a failure.
    print("6. Dataset  [none expected yet - see DATASET.md]")
    print(f"  {OK} status: NOT YET CREATED (by design)")
    for label, path in (("dataset", DATASET_ROOT), ("recordings", RECORDINGS_ROOT)):
        if path.is_dir():
            n_wav = sum(1 for _ in path.rglob("*.wav"))
            print(f"  {OK} {label:<11}{path}  ({n_wav:,} wav)")
        else:
            print(f"  {OK} {label:<11}{path}  (absent, as expected)")
    print("       Next: select a keyword, then design the dataset - DATASET.md 5")
    print()

    # Summary ---------------------------------------------------------------
    print("=" * 68)
    if required_failures:
        print(f"RESULT: NOT READY - {len(required_failures)} required check(s) failed")
        for f in required_failures:
            print(f"  - {f}")
        print("\nFix these first: see ENVIRONMENT_SETUP.md")
        rc = 1
    else:
        print("RESULT: READY - all required checks passed")
        rc = 0
    if warnings:
        print(f"\n{len(warnings)} warning(s) (not blocking): {', '.join(warnings)}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
