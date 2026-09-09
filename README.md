# SIH 2026 — PS 26172 · Low-Latency Efficient Voice Activator

Custom keyword spotting on an **ESP32-S3-WROOM-1-N16R8** with an **INMP441** I²S MEMS
microphone, streaming to a remote ASR server after detection.

> **Status: dataset-first restart.** Wake keyword **`Takshila`** /t̪əkˈʃiː.laː/ is confirmed
> ([`KEYWORD_SELECTION.md`](KEYWORD_SELECTION.md), D-011). The previously supplied corpus was
> deprecated and removed; **the new dataset does not exist yet** — see [`DATASET.md`](DATASET.md).

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

python scripts/verify_setup.py      # must print READY
python scripts/health_check.py      # git state, phase progress, blockers

# NOTE: there is no dataset to place. Building one is the current task - DATASET.md
```

The repository clones into **any** directory on Windows or Linux. Nothing
assumes a drive letter — see [`config/paths.py`](config/paths.py).

## Status

**Hardware knowledge, architecture, documentation and portability are complete and retained,
and the wake keyword is settled. There is no dataset, no implementation code, and nothing has
been measured on hardware in this repository.**

Next task: **resolve the pin map (B-1), build the recorder, run one measured pilot session.**
The dataset is fully specified in [`DATASET_SPEC.md`](DATASET_SPEC.md) — build from it.
Open blockers: **B-1** pin map (now critical path) · **B-6** no dataset yet · **B-3** Wi-Fi.
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
| [`DATASET.md`](DATASET.md) | **Dataset status (NOT YET CREATED) and the plan to build one** |
| [`KEYWORD_SELECTION.md`](KEYWORD_SELECTION.md) | Keyword research, scoring and licence audit |
| [`DATASET_SPEC.md`](DATASET_SPEC.md) | **The frozen dataset build specification (37 sections)** |
| [`DATASET_RESET_AUDIT.md`](DATASET_RESET_AUDIT.md) | Audit behind the dataset reset |
| [`GIT_HISTORY_DATASET_PURGE.md`](GIT_HISTORY_DATASET_PURGE.md) | Why no history rewrite is needed |
| [`HARDWARE.md`](HARDWARE.md) | Board, microphone, GPIO constraints, toolchain |
| [`ENVIRONMENT_SETUP.md`](ENVIRONMENT_SETUP.md) | Windows + Linux machine setup |
| [`EXPERIMENT_STATE.md`](EXPERIMENT_STATE.md) | What has been measured, and what has not |
| [`DECISIONS.md`](DECISIONS.md) | D-001…D-010, with reasoning and consequences |
| [`BUILD_LOG.md`](BUILD_LOG.md) | Append-only log with pre-declared pass bars |
| [`STORAGE_AUDIT.md`](STORAGE_AUDIT.md) | Historical record of the original machine |

## Layout

```
config/          machine-independent path + setting resolution
scripts/         setup, verification, health check
tools/           dataset-agnostic audio measurement
training/        feature pipeline, training, streaming evaluation   (empty)
firmware/        PlatformIO project - platformio.ini only, no src/  (empty)
server/          WebSocket audio sink, ASR, intent parser           (empty)
ui/              live demo dashboard                                (empty)
docs/            experiment records
data/            recordings + built dataset - NOT in Git (neither exists yet)
artifacts/       features, checkpoints, models - NOT in Git
```

## The finding that governs this project

> A positive class recorded from **one speaker** cannot be repaired downstream.
> Augmentation copies information; it does not add any. A predecessor project
> demonstrated **on hardware** that neither decision-logic tuning nor more public
> negative speech fixes it.

That is why this project restarts dataset-first: **speaker diversity in the positive
class is the primary design variable**, and it must be planned in before recording,
not discovered afterwards. It also forces a discipline the project must not relax:
**clip classification, streaming detection, false-trigger behaviour, wake-word latency
and real-world robustness are five different measures** and are never reported as one.

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
by the author. All reported measurements come from real data and real hardware.
