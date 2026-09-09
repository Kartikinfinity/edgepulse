# ENVIRONMENT_SETUP.md

Setting up a development machine for this project, on **Windows 11** or
**Linux**. Nothing here assumes a drive letter, a username, or the original
machine.

Every item is tagged **REQUIRED**, **RECOMMENDED** or **OPTIONAL**.

---

## 0. The fast path

```bash
git clone <repo-url> sih2026
cd sih2026

# Linux / macOS / Git Bash
bash scripts/setup.sh --dev

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Dev

python scripts/verify_setup.py
```

Then fetch the dataset (`DATASET_SETUP.md`) and re-run `verify_setup.py`.
If that prints **READY**, you are done. The rest of this document is the
manual route and the troubleshooting.

---

## 1. Git — **REQUIRED**

| OS | Install |
|---|---|
| Windows 11 | `winget install --id Git.Git -e` or <https://git-scm.com/download/win> |
| Debian/Ubuntu | `sudo apt update && sudo apt install -y git` |
| Fedora | `sudo dnf install -y git` |
| Arch | `sudo pacman -S git` |

```bash
git --version          # verified with 2.51.2
git clone <repo-url> sih2026
cd sih2026
```

The repository may be cloned into **any** directory.

## 2. Python — **REQUIRED**

> ### ⚠ Python 3.14 does not work
> TensorFlow publishes no wheels for 3.14. On the original machine the default
> `python` on PATH *was* 3.14, which silently fails at `pip install tensorflow`.
> **Use Python 3.10–3.13.** 3.13 is what this project is verified against.

| OS | Install |
|---|---|
| Windows 11 | `winget install --id Python.Python.3.13 -e` or python.org. Tick **"Add python.exe to PATH"**. |
| Debian/Ubuntu | `sudo apt install -y python3.13 python3.13-venv python3-pip` (or `python3.12`) |
| Fedora | `sudo dnf install -y python3.13` |
| Arch | `sudo pacman -S python` |

```bash
python --version       # must be 3.10.x - 3.13.x
py -3.13 --version     # Windows: the py launcher can select a version
```

## 3. Virtual environment — **REQUIRED**

The setup scripts do this. Manually:

```bash
# Linux / macOS
python3.13 -m venv .venv
source .venv/bin/activate

# Windows PowerShell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Windows Git Bash
py -3.13 -m venv .venv
source .venv/Scripts/activate
```

`.venv/` is git-ignored. Keep it inside the repository so the project stays
self-contained.

> **Low disk space?** Point pip's cache elsewhere before installing:
> `PIP_CACHE_DIR=/some/other/path` (Linux) or
> `$env:PIP_CACHE_DIR="D:\pip-cache"` (Windows). TensorFlow alone is ~600 MB.

## 4. Python packages — **REQUIRED**

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt              # REQUIRED
python -m pip install -r requirements-dev.txt          # RECOMMENDED
python -m pip install -r requirements-server.txt       # Phase G host only
```

| File | Contents | Tag |
|---|---|---|
| `requirements.txt` | numpy, scipy, soundfile, **tensorflow** | REQUIRED |
| `requirements-dev.txt` | pytest, matplotlib, librosa | RECOMMENDED |
| `requirements-server.txt` | faster-whisper, websockets | Phase G only |

### TensorFlow — **REQUIRED**

Comes from `requirements.txt`; no separate step.

```bash
python -c "import tensorflow as tf; print(tf.__version__, [d.device_type for d in tf.config.list_physical_devices()])"
```

Verified with **2.20.0**, CPU-only. GPU is **OPTIONAL** — the model is a small
DS-CNN and trains fine on CPU. On Linux, `pip install tensorflow[and-cuda]`
enables GPU; on Windows, native GPU support was dropped after TF 2.10, so use
WSL2 if you want CUDA. Neither is needed.

### PyTorch — **OPTIONAL**

The architecture targets TensorFlow Lite for Microcontrollers (`DECISIONS.md`
D-003), so **PyTorch is not used by any planned phase**. The problem statement
lists it as an allowed framework, so it is documented but deliberately not in
`requirements.txt`.

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Verified present on the original machine as 2.8.0+cpu.

## 5. PlatformIO + ESP32 toolchain — **REQUIRED for firmware only**

Not needed for Phases B–E or H.

```bash
python -m pip install --upgrade platformio
pio --version                       # verified with 6.1.19
```

The ESP32 toolchain is **not** installed by hand. `firmware/platformio.ini`
pins `espressif32@7.1.1`, and the first build downloads exactly that:

```bash
cd firmware
pio pkg install                     # fetch toolchain only (~2.4 GB, one time)
pio run                             # build (needs src/ - Phase A2)
```

> **Disk note.** The PlatformIO *core* directory holds ~2.4 GB of compiler
> toolchains and lives outside the repo by default (`~/.platformio`). That is
> correct — it is a per-machine tool install, like git. Only if that volume is
> short of space, set `PLATFORMIO_CORE_DIR` to somewhere roomier.

### Serial port and drivers

The ESP32-S3-N16R8 uses **native USB-Serial/JTAG** (`VID:PID 303A:1001`) — no
CP210x or CH340 driver is needed.

| OS | Port name | Notes |
|---|---|---|
| Windows 11 | `COM7`, `COM3`, … | driver is built in; **the number differs per machine** |
| Linux | `/dev/ttyACM0` | add yourself to the dialout group, then log out and back in |

```bash
# Linux: one-time permission fix
sudo usermod -aG dialout "$USER"

# either OS: what does PlatformIO see?
pio device list
```

Set the port only if auto-detection fails — in `.env`:

```
SIH_UPLOAD_PORT=COM7          # Windows
SIH_UPLOAD_PORT=/dev/ttyACM0  # Linux
```

**Never commit a port name into `platformio.ini`.**

## 6. Local configuration — **REQUIRED**

```bash
cp .env.example .env          # Linux/macOS
Copy-Item .env.example .env   # Windows PowerShell
```

`.env` is git-ignored and holds everything machine-specific: dataset location,
serial port, server ports, and (later) Wi-Fi credentials. Every value is
optional — the defaults are relative to the repository root.

Check what resolved:

```bash
python config/paths.py
```

> **Secrets rule.** Wi-Fi SSID/password and any token go in `.env` only.
> They must never reach Git, `platformio.ini`, or a committed header.

## 7. Dataset — **REQUIRED for Phases B–E**

See `DATASET_SETUP.md`. Short version: place `solvani_kws_release` at
`<repo>/data/solvani_kws_release` (or set `SIH_DATASET_ROOT`), then:

```bash
python scripts/verify_dataset.py           # spot-check, seconds
python scripts/verify_dataset.py --full    # every file, ~90 s
```

## 8. Verification — **REQUIRED**

```bash
python scripts/verify_setup.py     # Python, packages, git, pio, layout, dataset
python scripts/verify_dataset.py   # dataset integrity vs committed manifest
python scripts/health_check.py     # git state, phase progress, blockers, disk
```

`verify_setup.py` exits 0 only when every REQUIRED check passes.

## 9. Tests — **RECOMMENDED**

```bash
python -m pytest
```

There are **no tests yet** — `tests/` does not exist. Phase B1's exit bar
includes the first one (a synthetic-tone unit test for the feature pipeline).
pytest's configuration already lives in `pyproject.toml`.

## 10. Reproducing the dataset analysis — **OPTIONAL**

```bash
python tools/analyze_manifests.py     # structure, class counts, leakage check
python tools/audio_probe.py           # format audit, envelope
python tools/audio_probe_bands.py     # band-limited keyword localisation
```

Every figure quoted in `DATASET.md` comes from these three scripts. They are
read-only and work from any working directory.

## 11. Hardware bring-up — **REQUIRED before Phase F**

Blocked on the authoritative pin map (`CURRENT_HANDOFF.md` §6). Do not wire or
power anything until it is supplied and validated against `HARDWARE.md` §3.

⚠ The INMP441 is a **1.8–3.3 V** part. **Never connect it to 5 V.**

## 12. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `pip install tensorflow` finds no candidate | Python 3.14. Recreate the venv with 3.13. |
| `ModuleNotFoundError: config` | Run scripts as `python scripts/x.py` from anywhere; they bootstrap `sys.path` themselves. If you copied a script out of the repo, it will not work. |
| `verify_dataset.py` says dataset root missing | Dataset not placed, or `SIH_DATASET_ROOT` wrong. `python config/paths.py` shows what resolved. |
| `pio device list` shows nothing | Board unplugged, a charge-only USB cable, or (Linux) missing dialout membership. |
| `Activate.ps1 cannot be loaded` | `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`, or `Set-ExecutionPolicy -Scope Process RemoteSigned`. |
| Out of disk during install | Redirect `PIP_CACHE_DIR`; TensorFlow needs ~600 MB plus wheel cache. |
| Checksum mismatches after copying the dataset | Copied over a lossy path (cloud sync, zip round-trip). Re-extract from the original archive. |
