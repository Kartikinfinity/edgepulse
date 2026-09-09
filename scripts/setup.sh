#!/usr/bin/env bash
# SIH KWS - one-shot developer setup for Linux/macOS (and Git Bash on Windows).
#
#   bash scripts/setup.sh              # core deps
#   bash scripts/setup.sh --dev        # + pytest, matplotlib, librosa
#   bash scripts/setup.sh --server     # + faster-whisper (Phase G host only)
#   bash scripts/setup.sh --dev --server
#
# Creates .venv in the repository root and installs from requirements*.txt.
# Never touches anything outside the repository. Idempotent.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WANT_DEV=0
WANT_SERVER=0
for arg in "$@"; do
  case "$arg" in
    --dev)    WANT_DEV=1 ;;
    --server) WANT_SERVER=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

echo "=============================================================="
echo "SIH KWS setup"
echo "repository: $REPO_ROOT"
echo "=============================================================="

# --- 1. pick a Python -------------------------------------------------------
# TensorFlow has no wheels for 3.14 yet, so 3.13 and below only.
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    ver="$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "")"
    case "$ver" in
      3.10|3.11|3.12|3.13) PY="$cand"; break ;;
    esac
  fi
done
if [ -z "$PY" ]; then
  echo "ERROR: need Python 3.10-3.13 on PATH (TensorFlow has no 3.14 wheels)." >&2
  echo "See ENVIRONMENT_SETUP.md." >&2
  exit 1
fi
echo "[1/5] Python: $PY ($("$PY" --version 2>&1))"

# --- 2. virtual environment -------------------------------------------------
if [ ! -d .venv ]; then
  echo "[2/5] creating .venv"
  "$PY" -m venv .venv
else
  echo "[2/5] .venv already exists - reusing"
fi
VENV_PY=".venv/bin/python"
[ -x "$VENV_PY" ] || VENV_PY=".venv/Scripts/python.exe"   # Git Bash on Windows

# --- 3. dependencies --------------------------------------------------------
echo "[3/5] upgrading pip"
"$VENV_PY" -m pip install --quiet --upgrade pip

echo "[3/5] installing requirements.txt (this pulls TensorFlow; be patient)"
"$VENV_PY" -m pip install -r requirements.txt
if [ "$WANT_DEV" = "1" ]; then
  echo "[3/5] installing requirements-dev.txt"
  "$VENV_PY" -m pip install -r requirements-dev.txt
fi
if [ "$WANT_SERVER" = "1" ]; then
  echo "[3/5] installing requirements-server.txt"
  "$VENV_PY" -m pip install -r requirements-server.txt
fi

# --- 4. local config --------------------------------------------------------
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[4/5] created .env from .env.example (git-ignored; edit for this machine)"
else
  echo "[4/5] .env already exists - left untouched"
fi

# --- 5. verify --------------------------------------------------------------
echo "[5/5] verifying"
set +e
"$VENV_PY" scripts/verify_setup.py
rc=$?
set -e

cat <<EOF

--------------------------------------------------------------
Activate the environment with:
    source .venv/bin/activate          # Linux/macOS
    source .venv/Scripts/activate      # Git Bash on Windows

Then read CURRENT_HANDOFF.md - it names the exact next task.
--------------------------------------------------------------
EOF
exit $rc
