# EXPERIMENT_STATE.md

The experiment ledger: what has been measured **in this repository**, what has
not, and which numbers came from somewhere else.

`BUILD_LOG.md` holds the full records with their pre-declared pass bars. This
file is the index and, more importantly, the honest statement of what is
**still unmeasured**.

Last updated: 2026-09-09

---

## 1. Ledger

| ID | Title | Type | Status | Record |
|---|---|---|---|---|
| **EXP-000** | Discovery and project bootstrap | discovery | PASS | `BUILD_LOG.md` |
| **OPS-001** | Safe storage recovery + storage-strategy decision | operational | PASS | `BUILD_LOG.md` |
| **OPS-002** | Cross-machine portability and handoff preparation | operational | PASS | `BUILD_LOG.md` |

**Zero ML experiments. Zero hardware measurements. No model has been trained
in this repository.**

`docs/experiments/` is empty and awaits the first real experiment record.

## 2. What HAS been measured here

All from EXP-000, reproducible with `tools/analyze_manifests.py`,
`tools/audio_probe.py` and `tools/audio_probe_bands.py`.

### Dataset structure

| Measurement | Value |
|---|---|
| Total WAVs | 21,267 (+18 CSV/Markdown = 21,285 files, 685,589,976 B) |
| Format uniformity | 100 % of a 1,500-file random sample: mono / 16 kHz / 16-bit / exactly 16,000 frames |
| Files missing vs manifests | 0 |
| **Leakage: `source_id` spanning splits** | **0 / 2,387** |
| **Leakage: `original_source` spanning splits** | **0 / 2,387** |
| Unique positive recordings | **110** (77 train / 16 validation / **17 test**) |
| Positive speakers | **1** (`speaker_01`, 100 %) |
| Positive environments | 2 — `fan` (60), `classroom` (50) |
| Augmentation inflation | ×7.2 (110 recordings → 790 clips) |
| Phonetic hard negatives | 10 unique TTS phrases; 3 hardest are val/test-only |

### Dataset acoustics

| Measurement | Value |
|---|---|
| Keyword active span (300–3400 Hz, 110 unaugmented positives) | ~545 ms |
| Mean lead-in / trail-out | 235 ms / 221 ms |
| Peak-energy bin spread | std 5.1 bins = **±255 ms** — loosely centred, real positional spread |
| Speech-band (300–3400 Hz) energy fraction | positive **0.561** · negative 0.662 · background **0.538** |
| Clipping | 4 of 110 unaugmented positives contain a full-scale sample |
| RMS across positives | 0.034 – 0.485, mean 0.131 |

> The positive-vs-background speech-band gap of **0.023** is what forced
> `DECISIONS.md` D-008: an energy-only VAD separates almost nothing here.

### Host environment (original machine only — will differ on yours)

Intel i3-8100 4C/4T · 15.9 GB RAM · **no CUDA** · Windows 11 Pro 26200 ·
Python 3.13.9 · TensorFlow 2.20.0 · torch 2.8.0+cpu · PlatformIO 6.1.19 ·
`espressif32@7.1.1` · Arduino core 2.0.17 · ESP-IDF 4.4.

### Hardware presence (original machine, OPS-001/transition check)

ESP32-S3 enumerated as `VID:PID 303A:1001`, `SER=E0:72:A1:D7:20:24`, on
**COM7**. Presence only — **nothing was flashed and no chip readout was done**.

## 3. What has NOT been measured — the honest list

Nothing below has a number in this repository. Do not quote one.

| Area | Status |
|---|---|
| Board identity (chip rev, flash, PSRAM, heap) verified on *this* board | ❌ not measured — task **A4** |
| Actual I²S sample rate | ❌ not measured — task **A5** |
| 24-in-32 bit alignment, clipping, noise spectrum | ❌ not measured — task **A5** |
| Host↔device MFCC parity | ❌ not measured — task **B4** |
| Clip-level classification accuracy | ❌ no model exists |
| **Streaming detection rate** | ❌ no harness, no model |
| **False activations per hour** | ❌ never measured |
| **Wake-word latency** (keyword end → decision → first packet → ASR) | ❌ no firmware, no server |
| Inference time on device | ❌ not measured |
| Tensor arena / SRAM / flash footprint | ❌ not measured |
| Idle CPU % | ❌ not measured |
| Speaker-independent performance | ❌ **unmeasurable with this dataset** |
| Far-field / distance robustness | ❌ not measured |
| ASR decode time / real-time factor | ❌ not measured |
| Power consumption | ❌ not measured |
| Long-run stability | ❌ not measured |

## 4. Numbers carried over from the PRIOR build — `[prior-build]`

These come from a **different project** (`C:\Users\Menon\OneDrive\Desktop\SIH 2026`,
keyword **"Sentinel"**, 19 experiments, 29 commits) on the same hardware. They
are kept because they are real hardware measurements and they shaped this
project's decisions. **They are not results of this project.** Every one must be
re-measured before it is quoted.

| Measurement | Prior value | Used to justify |
|---|---|---|
| Inference, 49×13 MFCC int8 DS-CNN + ESP-NN | 84.17 ms | D-003, front-end sizing |
| Inference, 98×40 log-mel input | 2,240 ms (26.6× worse) | keeping the input small |
| ESP-NN build flags alone | **5.48×** speedup | D-003 |
| Tensor arena | 15,460 B | Phase-2 RAM budget |
| Firmware RAM / flash | 72,924 B / 374,653 B | Phase-2 RAM budget |
| Idle CPU at 200 ms cadence | **48 % of one core** | `ARCHITECTURE.md` §9 debt |
| MFCC host/device parity | max abs diff 0.000112, corr 1.0000000000 | B4's pass bar |
| Measured sample rate | 16,001.60 Hz (+0.010 %) | A5's expected value |
| Noise spectrum | 64.6 % of energy < 100 Hz | 125 Hz mel floor |
| Clip test set said 10.7 % false-fire; sliding windows measured **49.7 %** | 4.6× optimism | **D-005** |
| False-activation rate optimism vs natural speech | ~**12×** | **D-005** |
| Hard-negative mining: Speech Commands share of false positives | 0.14 % | D-004 — more public negatives will not help |

## 5. The five measures this project must never conflate

Stated here because collapsing them is exactly how the prior build produced
three misleading results in a row.

| # | Measure | Definition | Reported as |
|---|---|---|---|
| 1 | **Clip-level classification** | accuracy/precision/recall on centred 1.0 s clips | **secondary diagnostic only**, always labelled |
| 2 | **Streaming detector** | sliding windows over continuous audio at the real hop, with the real smoothing rule → **detections per spoken keyword** | **the headline metric** |
| 3 | **False-trigger behaviour** | **false activations per hour** on audio where the keyword is never spoken, *fresh* and never used for tuning | separately, always |
| 4 | **Wake-word latency** | keyword end → decision → first packet → server receipt → ASR final | the SIH-graded number |
| 5 | **Real-world robustness** | other speakers, distances, rooms, noise | currently **unmeasurable** — say so |

A figure swept and judged on the same audio is **provisional**, never a result.

## 6. Rules for the next experiment

1. Pre-declare the pass bar **before** running. `BUILD_LOG.md` has the template.
2. One change per experiment.
3. Record what the experiment does **not** prove — that section is mandatory.
4. Sweep an operating point on a SWEEP set, validate on a disjoint VALIDATE set.
5. Re-verify anything tagged `[prior-build]` before quoting it.
6. If a result looks surprisingly good, suspect the evaluation before the model.
   That instinct has been right every single time on this project.

## 7. Next experiments, in order

| Next | Depends on |
|---|---|
| **EXP-001** — validate the authoritative pin map against `HARDWARE.md` §3 | **blocked: pin map (B-1)** |
| **EXP-002** — board identity readout (A4) | board attached |
| **EXP-003** — I²S capture + sample-rate measurement (A5) | EXP-001 |
| **EXP-004** — feature pipeline determinism + synthetic-tone unit test (B1) | nothing — **can start now** |
| **EXP-005** — streaming evaluation harness, must be able to fail (C) | EXP-004 |
