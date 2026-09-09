# EXPERIMENT_STATE.md

The experiment ledger: what has been measured **in this repository**, what has not, and which
numbers came from somewhere else.

`BUILD_LOG.md` holds the full records with their pre-declared pass bars. This file is the index
and, more importantly, the honest statement of what is **still unmeasured**.

**Last updated:** 2026-09-09 — **reset with the dataset** (`DECISIONS.md` D-010).

---

## 1. Ledger

| ID | Title | Type | Status | Record |
|---|---|---|---|---|
| EXP-000 | Discovery and project bootstrap | discovery | PASS — **dataset findings VOIDED by D-010** | `BUILD_LOG.md` |
| **EXP-001** | **Custom wake keyword selection** | research | **PASS — `Takshila` confirmed (D-011)** | `BUILD_LOG.md` |
| OPS-001 | Safe storage recovery + storage-strategy decision | operational | PASS | `BUILD_LOG.md` |
| OPS-002 | Cross-machine portability and handoff preparation | operational | PASS | `BUILD_LOG.md` |
| OPS-003 | Dataset reset and active-context purge | operational | PASS | `BUILD_LOG.md` |

**Zero ML experiments. Zero hardware measurements. No model has ever been trained in this
repository.** `docs/experiments/` is empty.

## 2. What HAS been measured here, and still counts

Only environment and toolchain facts survive the reset. Everything else in EXP-000 was a
measurement **of the deprecated corpus** and is out of scope.

| Measurement | Value |
|---|---|
| Host (original machine) | i3-8100 4C/4T, 15.9 GB RAM, **no CUDA**, Windows 11 Pro 26200 |
| Toolchain | PlatformIO 6.1.19 · `espressif32@7.1.1` · Arduino core 2.0.17 · **ESP-IDF 4.4** |
| Python / ML | Python 3.13.9 · TensorFlow 2.20.0 · torch 2.8.0+cpu; Keras train + int8 TFLite export smoke-tested |
| I²S API available | legacy `driver/i2s.h` only — no `driver/i2s_std.h` in IDF 4.4 |
| Board presence | `VID:PID 303A:1001` enumerated on COM7 (original machine). **Presence only** — nothing flashed, no chip readout |

## 3. VOIDED by the dataset reset

Every dataset measurement previously recorded here — clip counts, format uniformity, split
leakage, unique-recording counts, speaker distribution, keyword position within the window,
speech-band energy fractions, RMS and clipping statistics — described the **deprecated
corpus**.

**They are out of scope and may not be quoted**, as background, as a baseline, or as
justification for a design choice (`DECISIONS.md` D-010). The techniques that produced them
survive in `tools/audio_probe.py` and `tools/audio_probe_bands.py`, both now dataset-agnostic,
and must be re-run against the new dataset once it exists.

## 4. What has NOT been measured — the honest list

Nothing below has a number in this repository. Do not quote one.

| Area | Status |
|---|---|
| Keyword selection | **done — `Takshila`, EXP-001 / D-011** |
| **Dataset: any statistic at all** | ❌ no dataset exists |
| Board identity verified on *this* board (chip rev, flash, PSRAM, heap) | ❌ not measured — task **A4** |
| Actual I²S sample rate | ❌ not measured — task **A5** |
| 24-in-32 bit alignment, clipping, noise spectrum | ❌ not measured — task **A5** |
| Host↔device MFCC parity | ❌ not measured — task **B4** |
| Clip-level classification accuracy | ❌ no model exists |
| **Streaming detection rate** | ❌ no harness, no model, no data |
| **False activations per hour** | ❌ never measured |
| **Wake-word latency** | ❌ no firmware, no server |
| Inference time on device | ❌ not measured |
| Tensor arena / SRAM / flash footprint | ❌ not measured |
| Idle CPU % | ❌ not measured |
| Speaker-independent performance | ❌ requires a speaker-disjoint test split, which requires the dataset |
| Far-field / distance robustness | ❌ not measured |
| ASR decode time / real-time factor | ❌ not measured |
| Power consumption, long-run stability | ❌ not measured |

## 5. Numbers carried over from the PRIOR build — `[prior-build]`

From a **different project** (keyword **"Sentinel"**, 19 experiments) on the same hardware.
Real hardware measurements that shaped this project's decisions. **They are not results of this
project** and must be re-measured before being quoted. Unaffected by the dataset reset — they
were never measurements of the deprecated corpus.

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
| False-activation optimism vs natural speech | ~**12×** | **D-005** |
| Hard-negative mining: public negatives' share of false positives | 0.14 % | more public negative speech does not help |

## 6. The five measures this project must never conflate

Stated here because collapsing them is exactly how a predecessor produced three misleading
results in a row. **This survives the dataset reset unchanged.**

| # | Measure | Definition | Reported as |
|---|---|---|---|
| 1 | **Clip-level classification** | accuracy on centred, complete-word clips | **secondary diagnostic only**, always labelled |
| 2 | **Streaming detection** | sliding windows over continuous audio at the real hop, real smoothing rule → **detections per spoken keyword** | **the headline metric** |
| 3 | **False-trigger behaviour** | **false activations per hour** on audio where the keyword is never spoken, *fresh*, never used for tuning | separately, always |
| 4 | **Wake-word latency** | keyword end → decision → first packet → server receipt → ASR final | the SIH-graded number |
| 5 | **Real-world robustness** | other speakers, distances, rooms, noise | only claimable with a speaker-disjoint test split |

A figure swept and judged on the same audio is **provisional**, never a result.

## 7. Rules for the next experiment

1. Pre-declare the pass bar **before** running. `BUILD_LOG.md` has the template.
2. One change per experiment.
3. Record what the experiment does **not** prove — that section is mandatory.
4. Sweep on a SWEEP set, validate on a disjoint VALIDATE set.
5. Re-verify anything tagged `[prior-build]` before quoting it.
6. **Never quote a figure from the deprecated corpus**, for any purpose.
7. If a result looks surprisingly good, suspect the evaluation before the model.

## 8. Next experiments, in order

| Next | Depends on |
|---|---|
| ~~EXP-001 — keyword selection~~ | **PASS — `Takshila` (D-011)** |
| ~~EXP-002 — dataset specification~~ | **PASS — now `RESEARCH_DATASET_ROADMAP.md` (Tier 2)** |
| ~~EXP-003 — KWS engine selection + pipeline verification~~ | **PASS — TFLM+ESP-NN, D-012** |
| **EXP-003** — recorder firmware + ONE measured pilot session | **blocked: pin map (B-1)** |
| **EXP-004** — Tier-1 collection against `DEMO_DATASET_SPEC.md` | **B-1 pin map** |
| **EXP-004** — validate the authoritative pin map against `HARDWARE.md` §3 | **blocked: pin map (B-1)** |
| **EXP-005** — board identity readout (A4) | board attached |
