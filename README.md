# SIH 2026 — PS 26172 · Low-Latency Efficient Voice Activator

Custom keyword spotting for the keyword **`solvani`** on an **ESP32-S3-WROOM-1-N16R8** with an
**INMP441** I²S MEMS microphone, streaming to a remote ASR server after detection.

```
INMP441 → I2S/DMA → ring buffer → VAD → MFCC → int8 DS-CNN (TFLM + ESP-NN)
        → M-of-N smoothing → WAKE → pre-roll + live PCM → WebSocket/Wi-Fi
        → server → ASR (faster-whisper) → transcript → intent/action → live dashboard
```

**Phase 1** targets maximum practical accuracy, false-trigger resistance, latency and demo
quality. The SIH limits of <256 KB RAM and <10 % idle CPU are **deliberately out of scope**
for this phase, and are measured and displayed rather than optimised against.

## Status

**Discovery and bootstrap complete. No implementation code exists yet, and nothing has been
measured on hardware in this tree.** See `STATUS.md`.

## Documents

| File | Contents |
|---|---|
| `CLAUDE.md` | Orientation for any new session — start here |
| `STATUS.md` | Where the project is, blockers, open risks |
| `BUILD_PLAN.md` | Phased roadmap with per-phase exit bars |
| `ARCHITECTURE.md` | System design and every justified deviation from the supplied plan |
| `DATASET.md` | Full measured analysis of the `solvani_kws_release` dataset |
| `HARDWARE.md` | Board, microphone, GPIO constraints, host, toolchain |
| `DECISIONS.md` | Irreversible decisions with reasoning and consequences |
| `BUILD_LOG.md` | Append-only experiment log with pre-declared pass bars |

## Layout

```
firmware/    PlatformIO project (ESP32-S3)
training/    feature pipeline, training, quantisation, streaming evaluation
server/      WebSocket audio sink, ASR, intent parser
ui/          live demo dashboard
tools/       dataset analysis utilities
data/        solvani_kws_release (21,267 WAVs, git-ignored)
artifacts/   features, models, checkpoints (git-ignored)
docs/        experiment records
```

## Reproducing the dataset analysis

```bash
python tools/analyze_manifests.py
python tools/audio_probe.py
python tools/audio_probe_bands.py
```

Every figure in `DATASET.md` comes from those three scripts.

## Honesty policy

No metric appears in this repository unless it was measured, and every measurement names its
source. Figures carried over from the earlier "Sentinel" build are tagged `[prior-build]` and
are treated as unverified here until re-measured. Detection and false-activation rates are
reported from a sliding-window simulation over continuous audio, never from centred clips —
see `DECISIONS.md` D-005 for the three separate times that distinction mattered.

## AI assistance disclosure

Firmware, tooling, analysis and documentation in this repository are developed with Claude Code
(Anthropic) acting as implementation and analysis assistant. Hardware wiring, physical test
execution and acceptance decisions are performed by the author. All reported measurements come
from the actual dataset and the actual hardware.
