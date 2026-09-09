# CURRENT_HANDOFF.md

**Read this first on a new machine or in a new session.** It is the practical
one-page-per-topic answer to "where is this project and what do I do now".

Last updated: 2026-09-09 · Handoff commit: see `git log -1`

---

## NEXT SESSION START

Do these six things, in order, before anything else.

```bash
# 1. get the code (any directory - nothing assumes a drive letter)
git clone <your-repo-url> sih2026 && cd sih2026

# 2. set up Python (pick ONE)
bash scripts/setup.sh --dev                                    # Linux / macOS / Git Bash
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Dev  # Windows PowerShell

# 3. there is NO dataset to place - building one is the current task (DATASET.md)

# 4. prove the machine is ready
python scripts/verify_setup.py        # must print READY
python scripts/health_check.py        # shows phase progress and blockers

# 5. read, in this order
#    CLAUDE.md -> DATASET.md -> PROJECT_STATE.md -> this file -> DECISIONS.md

# 6. then start the exact next task named below. Nothing before it.
```

**The exact next task is to resolve blocker B-1 (the pin map), then build the recorder and
run ONE measured pilot session.**

The keyword is settled (**`Takshila`**, D-011) and the dataset is **fully specified and frozen**
in **`DEMO_DATASET_SPEC.md`** (Tier 1) — **build from it, do not redesign it.**

**B-1 is now the critical path for the whole project**, not just for firmware: ≥70 % of positive
utterances must be recorded through the real INMP441 (`DEMO_DATASET_SPEC.md` §3), and re-recording
30 speakers later is not feasible. Order: pin map → wire → A4/A5 → recorder → pilot → collect.

**Do not train anything before the streaming evaluation harness exists.** The reason is in
`DECISIONS.md` D-005 and it is the single most expensive lesson this project has.

---

## 1. What has already been completed

| Area | State |
|---|---|
| Discovery: source documents, prior build, hardware, toolchain | ✅ done |
| **Dataset** | ❌ **RESET — deprecated and removed (D-010). None exists.** |
| **Keyword** | **`Takshila` /t̪əkˈʃiː.laː/ — CONFIRMED (D-011)** |
| Architecture design + 8 justified deviations | ✅ done, in `ARCHITECTURE.md` |
| Build plan with per-phase exit bars | ✅ done, in `BUILD_PLAN.md` |
| Decisions recorded with reasoning | ✅ done, in `DECISIONS.md` (D-001…D-010) |
| Storage cleanup and storage strategy | ✅ done, in `STORAGE_AUDIT.md` |
| Transition verification (board, toolchain) | ✅ done, in `BUILD_LOG.md` OPS-001 |
| Cross-machine portability layer | ✅ done, `BUILD_LOG.md` OPS-002 |
| Dataset reset + active-context purge | ✅ done, `BUILD_LOG.md` OPS-003 |

## 2. What has NOT been started

**No implementation code exists at all.** Not "partially" — none.

| Component | State |
|---|---|
| `training/` — feature pipeline, training, quantisation, streaming eval | **empty** |
| `firmware/src/` — any C/C++ | **empty** (`platformio.ini` is config only) |
| `server/` — WebSocket sink, ASR, intent parser | **empty** |
| `ui/` — demo dashboard | **empty** |
| `tests/` | **does not exist yet** |
| Trained model of any kind | **none** |
| Anything flashed to the board | **nothing** |
| Any measurement taken in this tree from hardware | **none** |

Only `tools/` has code: two dataset-agnostic audio measurement scripts.

## 3. Why the important decisions were made

Full reasoning in `DECISIONS.md`; the short version:

- **D-001 project layout** — one self-contained root, one drive. The original machine's C: was 100 % full; the project lives beside its dataset so nothing splits.
- **D-002 keyword** — **VOID.** The dataset that fixed the keyword is deprecated; selection is reopened (D-010).
- **D-003 Arduino core 2.0.17 / ESP-IDF 4.4** — the only stack with *measured* on-hardware evidence (84 ms inference with ESP-NN). The plan's ESP-IDF 5.x is better long-term but unproven here and costs hours we do not have.
- **D-004** — **VOID as a data claim**, but its lesson is now a *requirement* on the new dataset: see §5 and §7.
- **D-005 streaming metrics, never clip metrics** — the prior build reported clip numbers that were optimistic by 4.6× and ~12×, and once "solved" false positives by never firing at all. This is why the evaluation harness is built *before* the model.
- **D-006 ASR on the LAN host, raw PCM over WebSocket** — open-source-only rule, no internet dependence in a live demo, and latency is the graded metric, not bandwidth.
- **D-008 VAD is an indicator, not a KWS gate** — band energy is a weak discriminator against realistic backgrounds; re-measure on the new dataset before enabling any gate.
- **D-010 dataset reset** — the supplied corpus is deprecated and out of scope; the project restarts dataset-first.

## 4. Project root

**There is no fixed project root any more.** The repository works from any
directory on Windows or Linux. Everything resolves through `config/paths.py`,
which derives the root from its own file location.

- Original machine (historical only): `E:\sih2026`
- Your machine: wherever you cloned it.
- Override any path in `.env` (copy from `.env.example`; it is git-ignored).

## 5. Dataset — THERE IS NONE

```
DATASET STATUS: NOT YET CREATED
KEYWORD:        "Takshila" - CONFIRMED, binding (D-011)
ENGINE:         TFLite Micro + ESP-NN (D-012)
DATASET:        TIER 1 = DEMO_DATASET_SPEC.md (build now, 6 speakers)
                TIER 2 = RESEARCH_DATASET_ROADMAP.md (post-demo)
NEXT OBJECTIVE: B-1 pin map -> recorder -> ONE measured pilot -> collect.
```

The previously supplied corpus was **deprecated and removed from the project**
(`DECISIONS.md` D-010; audit in `DATASET_RESET_AUDIT.md`). It must not be used for training,
validation, testing, benchmarking, statistics, augmentation design, keyword selection, or any
conclusion. **Its numbers are out of scope — do not quote them, even as background.**

Where the new material will live, once it exists:

| What | Path | Note |
|---|---|---|
| Raw source recordings | `<repo>/data/recordings` (`SIH_RECORDINGS_ROOT`) | **keep permanently** |
| Built / curated dataset | `<repo>/data/dataset` (`SIH_DATASET_ROOT`) | git-ignored |

Neither exists. Full plan: **`DATASET.md`**.

### Requirements for the new dataset — learned the expensive way

A predecessor project proved **on hardware** that a positive class recorded from one speaker
cannot be repaired downstream: neither decision-logic tuning nor more public negative speech
fixed it. Augmentation copies information; it does not add any. So:

1. **Speaker diversity in the positive class is the primary design variable.** Plan for many
   speakers from the start.
2. **Keep every raw, uncut recording.** The deprecated corpus could not be re-cut at different
   offsets because its raw sessions were lost. Do not repeat that.
3. **Design positional spread deliberately** — a corpus of centred, complete words trains a
   model that fails on sliding windows.
4. **Splits must be recording-disjoint AND speaker-disjoint.** Only a speaker-disjoint test
   split can support a speaker-independence claim.
5. **Hard negatives are a first-class component**, and the hardest confusables belong in
   *training*, not only in validation/test.
6. **Write the evaluation protocol before collecting**, so the corpus supports streaming
   evaluation rather than clip accuracy.

## 6. Hardware

| Item | Value |
|---|---|
| MCU module | ESP32-S3-WROOM-1-**N16R8** (16 MB quad flash, 8 MB **octal** PSRAM, dual LX7 @ 240 MHz) |
| Microphone | INMP441 MEMS I²S — 24-bit, 64 SCK/WS frame, **VDD 1.8–3.3 V, never 5 V** |
| Link | native USB-Serial/JTAG, `VID:PID 303A:1001` |

**Current hardware status (original machine, 2026-09-09):** the board **is
attached** and enumerated on **COM7** (`SER=E0:72:A1:D7:20:24`). Nothing has
been flashed and no chip readout has been done, so chip rev / flash / PSRAM /
heap are still carried over from the prior build and are **unverified in this
tree** — that is task A4.

> On a new machine the port will differ. **Do not hard-code COM7.** Let
> PlatformIO auto-detect, or set `SIH_UPLOAD_PORT` in `.env`.

### Required pin map — STILL MISSING, this is blocker B-1

The authoritative INMP441 → ESP32-S3 pin mapping has **not** been supplied. It
is the only thing blocking hardware work. When it arrives, validate every pin
against the constraint table in `HARDWARE.md` §3 and record the check-off in
`BUILD_LOG.md` as EXP-001.

Non-negotiable constraints for this exact module:

| GPIO | Why it is unusable |
|---|---|
| **35, 36, 37** | wired to the **Octal PSRAM** on R8 modules |
| 26–32 | SPI flash bus |
| 0, 3, 45, 46 | strapping pins |
| 19, 20 | USB D− / D+ (killing these kills the console) |
| 43, 44 | UART0 |
| 22–25 | do not exist on ESP32-S3 |

Prior build used SCK→GPIO 6, WS→GPIO 5, SD→GPIO 4, L/R→GND. **Treat as
unconfirmed** until the authoritative map arrives.

## 7. THE CENTRAL PRINCIPLE — do not let this be forgotten

> **A positive class recorded from ONE speaker cannot be repaired downstream.**
> Augmentation copies information; it does not add any. A predecessor project
> demonstrated this **on hardware**: decision-logic tuning and more public negative
> speech were each independently exhausted, and neither fixed it.

This is why the project restarts dataset-first. Speaker diversity must be designed in
before recording, not discovered after training.

**Five things this project must keep separate and never conflate:**

| Measure | What it means | Status |
|---|---|---|
| **Clip-level classification** | accuracy on centred, complete-word clips | secondary diagnostic **only** |
| **Streaming detector** | sliding windows over continuous audio, real smoothing rule -> detections per spoken keyword, **false activations per hour** | **the headline metric** |
| **False-trigger behaviour** | measured on fresh audio where the keyword is never spoken, never used for tuning | must be measured separately |
| **Wake-word latency** | keyword end -> decision -> first packet -> ASR receipt | the SIH-graded number |
| **Real-world robustness** | other speakers, distance, noise, rooms | requires a speaker-disjoint test split |

## 8. Software environment

Full instructions: `ENVIRONMENT_SETUP.md`.

| Component | Requirement |
|---|---|
| Python | **3.10–3.13** (TensorFlow publishes no 3.14 wheels — a real trap, the original machine's default `python` is 3.14) |
| Core deps | `requirements.txt` — numpy, scipy, soundfile, tensorflow |
| Dev deps | `requirements-dev.txt` — pytest, matplotlib, librosa |
| Server deps | `requirements-server.txt` — faster-whisper, websockets (Phase G only) |
| Firmware | PlatformIO Core ≥ 6.1; `firmware/platformio.ini` pins `espressif32@7.1.1` |
| Verified on | Python 3.13.9 · numpy 2.2.6 · scipy 1.16.2 · TensorFlow 2.20.0 |

## 9. Current Git state

- Branch `master`, working tree clean at handoff.
- **No remote configured.** The push command is in the handoff report; nothing has been pushed.
- Dataset, artifacts, `.venv`, `.pio`, `.env` and all secrets are git-ignored.
- No dataset fingerprint is committed — there is no dataset. One will be reintroduced once the new dataset exists and its structure is known.

## 10. Exact next task and commands

**Phase A1 — Python environment** (mostly done by the setup script)

```bash
python scripts/verify_setup.py     # must say READY
```

**Phase A2 — PlatformIO skeleton.** `firmware/platformio.ini` already exists and
is portable. What is missing is a minimal `firmware/src/main.cpp` so the build
produces a binary.

```bash
cd firmware && pio run             # exit bar: produces a binary
```

**Phase B — host feature pipeline** (`training/features.py`): 25 ms frame /
20 ms hop, 512-point FFT with periodic Hann, 40 mel filters 125–7500 Hz,
13 MFCC via orthonormal DCT-II, 49×13 model input. Cache to
`artifacts/features_*.npz`. Normalisation statistics from **train only**.

**Phase C — the streaming evaluation harness** (`training/streaming_eval.py`),
before any model. Exit bar: a deliberately bad model must produce a plausibly
bad number. *A harness that cannot fail is not a harness.*

## 11. Known risks

| # | Risk | Note |
|---|---|---|
| R-1 | 110 positive utterances, one speaker | the binding constraint; Phase D |
| R-2 | 17 test positives | ±20 pp; streaming harness is the real bar |
| R-3 | Speaker-independence unmeasurable | never claim it |
| R-4 | Training is CPU-only on the original host (no CUDA) | fine for a small DS-CNN; a new machine with a GPU is a genuine upgrade |
| R-5 | Original project volume is a HDD | cache features to `.npz`; do not re-read 21k WAVs per epoch |
| R-6 | Phase-1 idle CPU will be high (~48 % measured previously) | a declared, displayed Phase-2 debt |
| R-7 | Raw uncut recordings do not exist | positives cannot be re-cut |
| R-8 | Judge speaks the keyword and nothing happens | speaker-dependence is real; be honest in the demo |

## 12. Things the next session must NOT redo

Wasting time re-deriving any of these is the most likely failure mode.

1. **Do not re-derive the hardware constraints or the architecture.** Both survived the reset intact and are recorded in `HARDWARE.md` and `ARCHITECTURE.md`.
2. **Do NOT reuse the deprecated corpus or any of its statistics** — for training, benchmarking, keyword selection, or even as background (D-010).
3. **Do not "discover" that a single-speaker positive class fails.** It is §7 and it is now a *design requirement* on the new dataset, not a finding to reproduce.
4. **Do not evaluate on centred clips and report it as detector accuracy.** D-005. This mistake has already cost this project three times.
5. **Do not migrate to ESP-IDF 5.x** without a measured reason. D-003.
6. **Do not optimise for <256 KB RAM or <10 % idle CPU.** Explicitly out of scope this phase — but *measure and display* both honestly.
7. **Do not re-run the storage audit.** `STORAGE_AUDIT.md` is a completed record of the original machine; it does not apply to a new one.
8. **Do not assume COM7, `E:\sih2026`, or any absolute path.** All removed; use `config/paths.py`.
9. **Do not re-install the PlatformIO toolchain by hand.** `pio run` fetches exactly what `platformio.ini` pins.
10. **Do not commit the dataset, `.env`, or Wi-Fi credentials.**

## 13. What is still needed from the user

| # | Item | Blocks |
|---|---|---|
| **B-1** | **Authoritative INMP441 → ESP32-S3 pin map** | A3, then A4–A6, F, I |
| **B-3** | **2.4 GHz Wi-Fi SSID + password** for the demo network | G3 onward |
| — | The board physically connected to *this* machine | A4–A6, F, I |
| — | *Optional, high value:* 3–5 additional speakers × ~20 utterances | the only true fix for R-1 |
| — | *Optional:* the raw uncut recordings, if they exist elsewhere | unlocks re-cutting positives |
