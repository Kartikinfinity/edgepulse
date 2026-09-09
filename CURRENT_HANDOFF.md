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

# 3. put the dataset in place - it is NOT in Git. See DATASET_SETUP.md
#    default location: <repo>/data/solvani_kws_release

# 4. prove the machine is ready
python scripts/verify_setup.py        # must print READY
python scripts/verify_dataset.py      # must print PASS
python scripts/health_check.py        # shows phase progress and blockers

# 5. read, in this order
#    CLAUDE.md -> PROJECT_STATE.md -> this file -> BUILD_PLAN.md -> DECISIONS.md

# 6. then start the exact next task named below. Nothing before it.
```

**The exact next task is `BUILD_PLAN.md` Phase A1 → A2, then B, then C.**
Phase A1 is already partly done by `scripts/setup.sh`; confirm with
`verify_setup.py` rather than assuming.

**Do not start Phase D/E/F/G/H before C exists.** The reason is in `DECISIONS.md`
D-005 and it is the single most expensive lesson this project has.

---

## 1. What has already been completed

| Area | State |
|---|---|
| Discovery: all source PDFs, prior build, dataset, hardware, toolchain | ✅ done |
| Dataset analysis (structure, leakage, acoustics) | ✅ done, measured, in `DATASET.md` |
| Architecture design + 8 justified deviations | ✅ done, in `ARCHITECTURE.md` |
| Build plan with per-phase exit bars | ✅ done, in `BUILD_PLAN.md` |
| Decisions recorded with reasoning | ✅ done, in `DECISIONS.md` (D-001…D-009) |
| Storage cleanup and storage strategy | ✅ done, in `STORAGE_AUDIT.md` |
| Transition verification (board, toolchain, dataset) | ✅ done, in `BUILD_LOG.md` OPS-001 |
| Cross-machine portability layer | ✅ done — this handoff |

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

Only `tools/` has code: three read-only dataset-analysis scripts.

## 3. Why the important decisions were made

Full reasoning in `DECISIONS.md`; the short version:

- **D-001 project layout** — one self-contained root, one drive. The original machine's C: was 100 % full; the project lives beside its dataset so nothing splits.
- **D-002 keyword `solvani`** — not a choice. The supplied dataset is the only positive audio that exists.
- **D-003 Arduino core 2.0.17 / ESP-IDF 4.4** — the only stack with *measured* on-hardware evidence (84 ms inference with ESP-NN). The plan's ESP-IDF 5.x is better long-term but unproven here and costs hours we do not have.
- **D-004 the positive class is the binding constraint** — see §7. Everything in Phase D targets it.
- **D-005 streaming metrics, never clip metrics** — the prior build reported clip numbers that were optimistic by 4.6× and ~12×, and once "solved" false positives by never firing at all. This is why the evaluation harness is built *before* the model.
- **D-006 ASR on the LAN host, raw PCM over WebSocket** — open-source-only rule, no internet dependence in a live demo, and latency is the graded metric, not bandwidth.
- **D-008 VAD is an indicator, not a KWS gate** — measured: band energy barely separates this data (positive 0.561 vs background 0.538).

## 4. Project root

**There is no fixed project root any more.** The repository works from any
directory on Windows or Linux. Everything resolves through `config/paths.py`,
which derives the root from its own file location.

- Original machine (historical only): `E:\sih2026`
- Your machine: wherever you cloned it.
- Override any path in `.env` (copy from `.env.example`; it is git-ignored).

## 5. Dataset location, structure, limitations

**Location** — default `<repo>/data/solvani_kws_release`; override with
`SIH_DATASET_ROOT` in `.env`. **Not in Git** (0.64 GB, 21,267 WAVs).
Getting it and verifying it: `DATASET_SETUP.md`.

**Structure**

```
data/solvani_kws_release/
├── dataset_balanced/          4,084 clips  (fast iteration loop)
└── dataset_full/             17,183 clips  (more negative diversity)
    ├── manifests/{train,validation,test}.csv
    └── {train,validation,test}/{positive,negative,background}/*.wav
```

Every clip: mono · 16 kHz · 16-bit PCM · exactly 16,000 frames (1.000 s).
Verified 100 % uniform on a 1,500-file random sample.

| variant | split | positive | negative | background |
|---|---|---:|---:|---:|
| full | train | 693 | 6,849 | 7,497 |
| full | validation | 80 | 815 | 890 |
| full | **test** | **17** | 163 | 179 |
| balanced | train | 693 | 1,386 | 1,176 |
| balanced | validation | 80 | 297 | 252 |
| balanced | **test** | **17** | 99 | 84 |

**Known limitations — do not rediscover these**

1. **110 unique positive utterances, one speaker (`speaker_01`), two rooms.** The 790 positive clips are ×7.2 augmentation of those 110. See §7.
2. **The test split holds 17 unique positive utterances.** A detection rate from it carries roughly ±20 percentage points. It cannot settle anything alone.
3. **Speaker-independence is impossible to measure** from this data. Never claim it.
4. Phonetic hard negatives are only **10 unique TTS phrases**, and the three hardest (`so many`, `sol vani`, `solvany`) appear only in validation/test — never in training.
5. Splits *are* genuinely recording-disjoint: 0 of 2,387 source recordings span a split. The leakage check passes.
6. Clips are 1.0 s windows containing the whole word; the device sees fragments. This mismatch is the trap in `DATASET.md` §7.
7. The **raw uncut recordings do not exist** on the original machine (four independent searches). Positives cannot be re-cut at new offsets. New positive audio must be recorded or synthesised.

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

## 7. THE CENTRAL ML FINDING — do not let this be forgotten

> The dataset holds **21,267 WAV files**, which looks generous and is not.
> The positive class is approximately **110 unique utterances from ONE
> speaker**, inflated to 790 clips by augmentation. The negative class draws on
> thousands of speakers.

The prior build died on exactly this asymmetry and proved **on hardware** that
decision-logic tuning and more negative data do not fix it. Augmentation copies
information; it does not add any.

**Four things this project must keep separate and never conflate:**

| Measure | What it means | Status |
|---|---|---|
| **Clip-level classification** | accuracy on centred 1.0 s clips | secondary diagnostic **only** |
| **Streaming detector** | sliding windows over continuous audio, real smoothing rule → detections per spoken keyword, **false activations per hour** | **the headline metric** |
| **False-trigger behaviour** | measured on audio where the keyword is never spoken, fresh, never used for tuning | must be measured separately |
| **Wake-word latency** | keyword end → decision → first packet → ASR receipt | the SIH-graded number |
| **Real-world robustness** | other speakers, distance, noise, rooms | currently **unmeasurable** with this data |

Phase C builds the streaming harness. Phase D attacks the positive-class
ceiling. Do not reorder them.

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
- `dataset_manifest/` **is** committed — that is how another machine proves it has the right data without the WAVs.

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

1. **Do not re-analyse the dataset from scratch.** It is measured in `DATASET.md`; reproduce with `python tools/analyze_manifests.py` if you want to confirm.
2. **Do not re-litigate the keyword.** `solvani` is fixed by the data (D-002).
3. **Do not "discover" that positives are scarce.** It is §7, it is D-004, it is the whole point of Phase D.
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
