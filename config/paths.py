"""Machine-independent path and setting resolution for the SIH KWS project.

Nothing in this repository may hard-code an absolute path. Every script resolves
its locations through this module, which works the same on Windows and Linux and
from any current working directory.

Resolution order for every setting (first hit wins):

    1. a real environment variable
    2. a KEY=VALUE line in <project root>/.env      (git-ignored, machine-specific)
    3. the built-in default, always relative to the project root

The project root is derived from this file's own location, so cloning the
repository into any directory just works.

Usage from any script in the repo::

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from config.paths import DATASET_ROOT, PROJECT_ROOT

This module imports only the standard library, on purpose: it must be usable
before any dependency has been installed (``scripts/verify_setup.py`` relies on
that).
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Project root: <root>/config/paths.py  ->  parents[1] is <root>
# --------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]

ENV_FILE: Path = PROJECT_ROOT / ".env"
ENV_EXAMPLE: Path = PROJECT_ROOT / ".env.example"


def _load_env_file(path: Path) -> dict[str, str]:
    """Parse a minimal KEY=VALUE file. No dependency on python-dotenv."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        # strip one layer of matching quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


_FILE_ENV: dict[str, str] = _load_env_file(ENV_FILE)


def setting(name: str, default: str | None = None) -> str | None:
    """Return a configuration value, or ``default`` if it is unset/empty."""
    for source in (os.environ.get(name), _FILE_ENV.get(name)):
        if source is not None and source.strip() != "":
            return source
    return default


def path_setting(name: str, default_relative: str) -> Path:
    """Resolve a path setting.

    A relative value is interpreted relative to the project root, so a
    checkout can be moved anywhere. An absolute value is honoured as-is, which
    is what lets a machine keep the dataset on a different drive.
    """
    raw = setting(name)
    if raw:
        expanded = Path(os.path.expandvars(os.path.expanduser(raw)))
        return expanded if expanded.is_absolute() else (PROJECT_ROOT / expanded)
    return PROJECT_ROOT / default_relative


def flag(name: str, default: bool = False) -> bool:
    """Read a boolean setting ('1', 'true', 'yes', 'on' are true)."""
    raw = setting(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --------------------------------------------------------------------------
# Directories
# --------------------------------------------------------------------------
# NOTE: there is currently NO approved dataset. The previous corpus was
# deprecated and removed from the project (see DATASET.md and DECISIONS.md
# D-010). DATASET_ROOT points at the directory where the NEW dataset will be
# built; it does not exist yet, and code must not assume it does.
DATASET_ROOT: Path = path_setting("SIH_DATASET_ROOT", "data/dataset")
RECORDINGS_ROOT: Path = path_setting("SIH_RECORDINGS_ROOT", "data/recordings")
ARTIFACTS_DIR: Path = path_setting("SIH_ARTIFACTS_DIR", "artifacts")
DOCS_DIR: Path = PROJECT_ROOT / "docs"
EXPERIMENTS_DIR: Path = DOCS_DIR / "experiments"
FIRMWARE_DIR: Path = PROJECT_ROOT / "firmware"
TRAINING_DIR: Path = PROJECT_ROOT / "training"
SERVER_DIR: Path = PROJECT_ROOT / "server"
UI_DIR: Path = PROJECT_ROOT / "ui"
TOOLS_DIR: Path = PROJECT_ROOT / "tools"
SCRIPTS_DIR: Path = PROJECT_ROOT / "scripts"

# Split names are a conventional default. Class names and any variant scheme
# belong to the dataset design, which has not been done yet - do not hard-code
# a class list here until DATASET.md defines one.
SPLITS: tuple[str, ...] = ("train", "validation", "test")

# --------------------------------------------------------------------------
# Optional external corpora, e.g. a public negative/background source.
# Nothing requires these. They are candidate material for the new dataset.
# --------------------------------------------------------------------------
SPEECH_COMMANDS_ROOT_RAW: str | None = setting("SIH_SPEECH_COMMANDS_ROOT")
SPEECH_COMMANDS_ROOT: Path | None = (
    Path(os.path.expandvars(os.path.expanduser(SPEECH_COMMANDS_ROOT_RAW)))
    if SPEECH_COMMANDS_ROOT_RAW
    else None
)

# --------------------------------------------------------------------------
# Hardware / network settings (never contain secrets in this file)
# --------------------------------------------------------------------------
UPLOAD_PORT: str | None = setting("SIH_UPLOAD_PORT")      # e.g. COM7 or /dev/ttyACM0
MONITOR_BAUD: int = int(setting("SIH_MONITOR_BAUD", "115200"))
ASR_SERVER_HOST: str = setting("SIH_ASR_SERVER_HOST", "0.0.0.0")
ASR_SERVER_PORT: int = int(setting("SIH_ASR_SERVER_PORT", "8765"))
DASHBOARD_PORT: int = int(setting("SIH_DASHBOARD_PORT", "8080"))


def describe() -> str:
    """Human-readable summary, used by the verification scripts."""
    lines = [
        f"project root      : {PROJECT_ROOT}",
        f".env present      : {ENV_FILE.is_file()}",
        f"dataset root      : {DATASET_ROOT}",
        f"dataset present   : {DATASET_ROOT.is_dir()}  (none approved yet - see DATASET.md)",
        f"recordings root   : {RECORDINGS_ROOT}",
        f"artifacts dir     : {ARTIFACTS_DIR}",
        f"upload port       : {UPLOAD_PORT or '(auto-detect)'}",
    ]
    if SPEECH_COMMANDS_ROOT:
        lines.append(f"speech commands   : {SPEECH_COMMANDS_ROOT}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe())
