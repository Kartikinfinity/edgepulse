# CLAUDE.md — orientation for any future session

**Project:** SIH 2026 · PS **26172** — *Low Latency and Efficient Voice Activator for Edge Devices* (ISRO / Dept. of Space)
**Build phase:** Phase 1 — maximum practical accuracy + demo quality. **RAM/CPU budgets deliberately out of scope.**
**Keyword:** `solvani` (sol-vaa-nee) — fixed by the supplied dataset.

---

## 0. Read this before touching anything

1. This tree is a **fresh build**. A *previous, different* build exists at
   `C:\Users\Menon\OneDrive\Desktop\SIH 2026` (keyword "Sentinel", 19 experiments, git history).
   Its documents are **evidence from real hardware measurements** and are cited throughout
   these docs as `[prior-build]`. They are **not** this project's state. Anything marked
   `[prior-build]` must be **re-verified** here before it is quoted as a result.
2. **Never state a metric that was not measured in this tree.** If it was not measured, say
   "not measured". The prior build failed three times specifically because an evaluation was
   optimistic; see `DECISIONS.md` D-005 and `DATASET.md` §7.
3. Read in this order: `STATUS.md` (where we are) → `BUILD_PLAN.md` (what is next) →
   `DECISIONS.md` (why things are the way they are) → the topic doc you need.

---

## 1. Where things live — and why not on C:

**C: has 0 bytes free** (128 GB NVMe, measured 2026-09-09). D: and E: are partitions of a
1 TB SATA HDD with 337 GB / 446 GB free. Therefore:

| What | Path |
|---|---|
| **Project root (this tree)** | `E:\sih2026` |
| Dataset (21,267 WAVs) | `E:\sih2026\data\solvani_kws_release` |
| Python venv | `E:\sih2026\.venv` (create with `PIP_CACHE_DIR` on E:) |
| PlatformIO **build** dir | `E:\sih2026\.pio` (set `build_dir` in `platformio.ini`) |
| PlatformIO **core** dir | `C:\Users\Menon\.platformio` (2.96 GB, **already installed — do not reinstall**) |
| Models / features / checkpoints | `E:\sih2026\artifacts` (git-ignored) |
| Prior build (reference only) | `C:\Users\Menon\OneDrive\Desktop\SIH 2026` |
| Source PDFs + zips | `C:\Users\Menon\OneDrive\Desktop\sih 2026 2.0` |

> **Windows/Python path trap that has already cost this project time.** Git-Bash POSIX paths
> (`/e/sih2026`) are **not** understood by `C:\Python314\python`; it resolves `/e/...` to
> `C:\e\...` on the *current* drive and silently fills the full C: disk. **Always pass
> Windows paths (`E:\sih2026\...`) to Python**, POSIX paths to bash tools.

---

## 2. The pipeline in one line

```
INMP441 --I2S/DMA--> ring buffer --> VAD --> MFCC --> int8 DS-CNN (TFLM+ESP-NN)
   --> M-of-N smoothing --> WAKE --> pre-roll + live PCM --WebSocket/Wi-Fi-->
   server --> ASR (faster-whisper) --> transcript --> intent/action --> live dashboard
```

Full detail and every justified deviation: `ARCHITECTURE.md`.

---

## 3. The one thing that decides whether this project succeeds

The dataset's **positive class is 110 unique utterances from ONE speaker (`speaker_01`) in
two rooms**, inflated to 790 clips by augmentation. The negative class has thousands of
speakers. The prior build died on exactly this asymmetry and proved, on hardware, that
decision-logic tuning and more negative data do **not** fix it.

Everything in `BUILD_PLAN.md` Phase D is aimed at that single constraint. Do not spend time
tuning thresholds hoping to escape it.

---

## 4. Ground rules for work in this tree

- **Measure, then claim.** Every number in a doc carries a source (experiment ID or tool run).
- **Evaluate the way the device runs**: sliding windows over continuous audio, never centred
  1.0 s clips. A clip-level accuracy figure is *not* a detector figure. (`DECISIONS.md` D-005)
- **Feature parity is mandatory.** Host and device MFCC must match numerically before any
  on-device accuracy claim. There is a parity test for this; run it after any front-end change.
- **One change per experiment.** Log it in `BUILD_LOG.md` with a pre-declared pass/fail bar.
- Prefer editing an existing doc over adding a new one. Keep `STATUS.md` current.

---

## 5. Commands

```bash
# Python (training / server) — venv lives on E:
E:/sih2026/.venv/Scripts/python.exe training/train.py

# Firmware
cd E:/sih2026/firmware && pio run              # build
pio run -t upload                              # flash
pio device monitor -b 921600
```

`PLATFORMIO_CORE_DIR` must stay `C:\Users\Menon\.platformio`. Only `build_dir` moves to E:.

---

## 6. Hard blockers currently open

Tracked in `STATUS.md` §Blockers. As of bootstrap: **authoritative pin map**, **Wi-Fi
credentials**, and **the ESP32 is not currently attached** (no `VID_303A` device enumerated).
