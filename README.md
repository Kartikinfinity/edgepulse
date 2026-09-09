# SIH 2026 — PS 26172 · Low-Latency Efficient Voice Activator

Custom keyword spotting for the wake word **`solvani`** on an
**ESP32-S3-WROOM-1-N16R8** with an **INMP441** I²S MEMS microphone, streaming to
a remote ASR server after detection.

```
INMP441 → I2S/DMA → ring buffer → VAD → MFCC → int8 DS-CNN (TFLM + ESP-NN)
        → M-of-N smoothing → WAKE → pre-roll + live PCM → WebSocket/Wi-Fi
        → server → ASR (faster-whisper) → transcript → intent/action → live dashboard
```

**Phase 1** targets maximum practical accuracy, false-trigger resistance,
latency and demo quality. The SIH limits of <256 KB RAM and <10 % idle CPU are
**deliberately out of scope** for this phase — they are measured and displayed
honestly, not optimised against.

---

## Start here

**New machine or new session? Read [`CURRENT_HANDOFF.md`](CURRENT_HANDOFF.md).**
It opens with a NEXT SESSION START block.

```bash
git clone <repo-url> sih2026 && cd sih2026

bash scripts/setup.sh --dev                                      # Linux / macOS / Git Bash
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Dev  # Windows

# place the dataset (not in Git) - see DATASET_SETUP.md
python scripts/verify_setup.py      # must print READY
python scripts/verify_dataset.py    # must print PASS
python scripts/health_check.py      # git state, phase progress, blockers
```

The repository clones into **any** directory on Windows or Linux. Nothing
assumes a drive letter — see [`config/paths.py`](config/paths.py).

## Status

**Discovery, documentation and portability are complete. No implementation code
exists yet, and nothing has been measured on hardware in this repository.**

Next task: `BUILD_PLAN.md` **A1 → A2 → B → C**.
Open blockers: **B-1** authoritative pin map · **B-3** Wi-Fi credentials.
Live detail in [`STATUS.md`](STATUS.md).

## Documents

| File | Contents |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Orientation and safety rules for an AI session |
| [`CURRENT_HANDOFF.md`](CURRENT_HANDOFF.md) | **Cross-machine handoff — the practical entry point** |
| [`PROJECT_STATE.md`](PROJECT_STATE.md) | What exists and what does not |
| [`STATUS.md`](STATUS.md) | Live status, blockers, open risks |
| [`BUILD_PLAN.md`](BUILD_PLAN.md) | Phases A–I with per-phase exit bars |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System design and every justified deviation |
| [`DATASET.md`](DATASET.md) | Measured dataset analysis |
| [`DATASET_SETUP.md`](DATASET_SETUP.md) | Obtaining and verifying the dataset |
| [`HARDWARE.md`](HARDWARE.md) | Board, microphone, GPIO constraints, toolchain |
| [`ENVIRONMENT_SETUP.md`](ENVIRONMENT_SETUP.md) | Windows + Linux machine setup |
| [`EXPERIMENT_STATE.md`](EXPERIMENT_STATE.md) | What has been measured, and what has not |
| [`DECISIONS.md`](DECISIONS.md) | D-001…D-009, with reasoning and consequences |
| [`BUILD_LOG.md`](BUILD_LOG.md) | Append-only log with pre-declared pass bars |
| [`STORAGE_AUDIT.md`](STORAGE_AUDIT.md) | Historical record of the original machine |

## Layout

```
config/          machine-independent path + setting resolution
scripts/         setup, verification, health check, manifest generation
tools/           read-only dataset analysis
training/        feature pipeline, training, streaming evaluation   (empty)
firmware/        PlatformIO project - platformio.ini only, no src/  (empty)
server/          WebSocket audio sink, ASR, intent parser           (empty)
ui/              live demo dashboard                                (empty)
docs/            experiment records
dataset_manifest/ committed dataset fingerprint (counts + checksums)
data/            the dataset itself - NOT in Git
artifacts/       features, checkpoints, models - NOT in Git
```

## The finding that governs this project

> The dataset holds **21,267 WAV files**, which looks generous and is not. The
> positive class is approximately **110 unique utterances from ONE speaker**,
> inflated to 790 clips by augmentation. The negative class draws on thousands
> of speakers.

Augmentation copies information; it does not add any. This asymmetry — not
architecture, not quantisation, not threshold tuning — decides whether the
system works. It also forces a discipline the project must not relax: **clip
classification, streaming detection, false-trigger behaviour, wake-word latency
and real-world robustness are five different measures** and are never reported
as one.

## Honesty policy

No metric appears in this repository unless it was measured, and every
measurement names its source. Figures carried over from an earlier build with a
different keyword are tagged `[prior-build]` and treated as unverified here.
Detection and false-activation rates are reported from a sliding-window
simulation over continuous audio, never from centred clips — see
[`DECISIONS.md`](DECISIONS.md) D-005 for the three separate times that
distinction mattered.

## AI assistance disclosure

Firmware, tooling, analysis and documentation in this repository are developed
with Claude Code (Anthropic) acting as implementation and analysis assistant.
Hardware wiring, physical test execution and acceptance decisions are performed
by the author. All reported measurements come from the actual dataset and the
actual hardware.
