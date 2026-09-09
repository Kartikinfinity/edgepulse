# BUILD_PLAN.md — Phase 1 (demo-grade, 12–16 h)

Ordering principle, taken from the supplied story document and endorsed by the prior build's
failures: **make the audio path work end-to-end with a dummy decision first, then insert the
model.** Never debug the network and the neural network at the same time.

Each phase has an explicit **exit bar**. A phase is not done until its bar is measured and
written into `BUILD_LOG.md`.

Legend: 🔴 blocked · 🟡 partially blocked · 🟢 ready.

---

## Phase A — Environment + hardware bring-up  (~1.5 h) 🟡

| # | Task | Exit bar |
|---|---|---|
| A1 | Create Python venv on E: (`PIP_CACHE_DIR=E:\...`), install numpy/scipy/tf/soundfile/librosa | `import` smoke test passes; nothing written to C: |
| A2 | PlatformIO project skeleton, `build_dir` on E:, board overrides for N16R8 | `pio run` produces a binary |
| A3 | **Apply the authoritative pin map**, validate every pin against `HARDWARE.md` section 3 | written check-off table, GPIO 35/36/37 confirmed unused |
| A4 | Flash a hardware-identity probe: chip rev, cores, flash, PSRAM, heap | matches `HARDWARE.md` section 1 or the doc is corrected |
| A5 | I2S capture, dump 5 s PCM, **measure the true sample rate** against `esp_timer` | rate within 0.5 % of 16 kHz; 24-in-32 alignment confirmed on every sample; 0 clipped |
| A6 | Capture a WAV and **listen to it** | natural pitch and speed, speech clearly audible |

🔴 **A3 is blocked** on the authoritative pin map. 🔴 **A4–A6 are blocked** on the board being
attached (no `VID_303A` device is currently enumerated).
A1–A2 and all of Phase B are unblocked and run first.

## Phase B — Host feature pipeline + parity  (~1.5 h) 🟢

| # | Task | Exit bar |
|---|---|---|
| B1 | `training/features.py`: 25 ms/20 ms, 512-FFT Hann, 40 mel 125–7500 Hz, 13 MFCC (orthonormal DCT-II) | deterministic; unit test on a synthetic tone |
| B2 | Build feature tensors from the manifests; cache to `artifacts/features_*.npz` | shapes 49x13; split counts equal `DATASET.md` section 2 |
| B3 | Per-coefficient mean/std over **train only**; emit `kws_params.h` | no val/test statistics leak into normalisation |
| B4 | Port the identical maths to C++ and run the **host/device parity test** | max abs diff < 1e-3 and correlation > 0.9999 (bar from `[prior-build]` 0.000112 / 1.0000000000) |

*B4's device half needs the board; the C++ can be written and unit-tested on host first.*

## Phase C — Streaming-honest evaluation harness  (~1.5 h) 🟢 — **build this before the model**

This is the phase the prior build wishes it had done first.

| # | Task | Exit bar |
|---|---|---|
| C1 | `training/streaming_eval.py`: concatenate held-out clips into continuous audio with realistic gaps and noise floors | reproducible with a fixed seed; total duration and keyword count reported |
| C2 | Slide the real 1.0 s window at the real hop; apply the real threshold + M-of-N + refractory | outputs detections-per-spoken-keyword and **false activations per hour** |
| C3 | Two disjoint stream sets: **SWEEP** (choose the operating point) and **VALIDATE** (never used for tuning) | seeds and file lists recorded |
| C4 | Report clip metrics too, clearly labelled *secondary diagnostic* | both appear side by side in the report |

**Exit bar for Phase C:** running a deliberately bad model through the harness produces a
plausibly bad number. A harness that cannot fail is not a harness.

## Phase D — Attack the positive-class ceiling  (~2.5 h) 🟢 — **highest-value phase**

`DATASET.md` section 3: 110 utterances, one speaker, two rooms. Everything else is downstream of this.

| # | Task | Exit bar |
|---|---|---|
| D1 | **Time-shift augmentation** + explicit **partial-keyword negatives** (word >=50 % outside the window) | training window distribution matches inference; measured on the Phase-C harness |
| D2 | **Expand phonetic hard negatives** with open-source TTS — the shipped set is only 10 phrases, and the 3 hardest are not in train | >=40 confusable phrases across many synthetic voices, in train |
| D3 | **A-7 experiment: synthetic positives.** Generate `solvani` across many open-source TTS voices. Train A (real only) vs B (real + synthetic) | decided **only** on real held-out positives via Phase C. Ship B only if it wins |
| D4 | SpecAugment (time/freq masking) in the feature domain | A/B on the Phase-C harness |
| D5 | Room-impulse-response reverb + INMP441 channel simulation (band-limit to the mic's response) | A/B on the Phase-C harness |
| D6 | *If the user can record:* 3–5 additional speakers x ~20 utterances | the only true fix; ~15 min per person. Recommended, not blocking |

## Phase E — Model, quantisation, export  (~2 h) 🟢

| # | Task | Exit bar |
|---|---|---|
| E1 | DS-CNN baseline (prior build's 7,779-param shape as the reference point) | trains; Phase-C numbers recorded |
| E2 | Since Phase 1 lifts RAM limits: widen/deepen, and try a **BC-ResNet** variant | pick on Phase-C metric per millisecond of measured inference |
| E3 | Full-integer int8 conversion, representative dataset from train only | float vs int8 delta measured and recorded (prior build: never cost accuracy) |
| E4 | Export to a C array + generated params header | byte size recorded |
| E5 | Front-end size benchmark 49x13 vs 49x20 vs 49x40 **on hardware** | measured ms/inference per variant |

## Phase F — On-device KWS  (~2 h) 🔴 needs board

| # | Task | Exit bar |
|---|---|---|
| F1 | TFLM + **ESP-NN** with `-DESP_NN=1 -DCONFIG_IDF_TARGET_ESP32S3=1` | inference time measured; prior build got 5.48x from these two flags alone |
| F2 | Streaming features: one frame per hop, ring of 49 | no 49-frame recompute; CPU % measured |
| F3 | Dual-core split: capture on Core 0, features+KWS on Core 1 | no dropped DMA buffers under load |
| F4 | Live controlled tests: **Test 1** keyword x10; **Test 2** 60 s+ with the keyword never spoken | detection rate and false activations/min, both from *fresh* audio |
| F5 | Report the Phase-2 metrics honestly: idle CPU %, SRAM, arena, flash | numbers on the dashboard, not hidden |

## Phase G — Streaming + ASR server  (~2 h) 🟡 needs Wi-Fi credentials

| # | Task | Exit bar |
|---|---|---|
| G1 | Server: WebSocket audio sink, WAV assembly, clock-offset handshake | round-trips synthetic audio from a host test client |
| G2 | faster-whisper `base.en` int8 CPU; measure decode time on the i3-8100 | real-time factor measured; fall back to `tiny.en` if the demo drags |
| G3 | Device: persistent WS in LISTENING, 500 ms pre-roll, PCM16 frames on wake | audio arrives complete, keyword onset intact |
| G4 | End-of-utterance detection + 8 s cap | stream closes reliably; no truncated commands |
| G5 | **Latency instrumentation** end to end | the SIH metric (keyword end to server receipt) measured, not estimated |
| G6 | Intent parser + action, echoed back to the device | visible outcome on both dashboard and board |

## Phase H — Demo UI  (~2.5 h) 🟢 (buildable against a simulator)

| # | Task | Exit bar |
|---|---|---|
| H1 | Telemetry schema (device to server to browser) + a **replay simulator** so the UI is developable with no hardware | UI runs from recorded telemetry |
| H2 | Pipeline flow diagram with live stage lighting | a non-technical viewer can name the stages |
| H3 | All panels in `ARCHITECTURE.md` section 7 | every listed field present or explicitly "not measured" |
| H4 | Latency breakdown + resource panel (incl. the Phase-2 gap) | honest values, no fabrication |
| H5 | Event timeline with export | a full demo run can be replayed afterwards |

## Phase I — Validation + rehearsal  (~1 h) 🔴 needs board

| # | Task | Exit bar |
|---|---|---|
| I1 | **Fresh** validation runs at the chosen operating point (never the sweep audio) | detection rate + false activations/hour |
| I2 | A long negative run for the per-hour figure | >=20 min continuous; prior build never exceeded 40 s |
| I3 | Full rehearsal: cold boot to transcript to action, 5 consecutive times | 5/5 without intervention, or the failures are documented |
| I4 | Failure drills: Wi-Fi drop, server restart, mic unplugged | system degrades visibly and recovers |

---

## Critical path and parallelism

```
A1,A2 --> B1,B2,B3 --> C1..C4 --> D1..D5 --> E1..E4 --> [board] F --> G --> I
                            \--> H1..H5 (parallel, simulator-driven)
```

Phases B, C, D, E and H need **no hardware**. If the board stays unattached, roughly
**9 of the 16 hours of work is still unblocked** — start there and do not idle.

## Time budget

| Phase | Hours |
|---|---|
| A environment + bring-up | 1.5 |
| B features + parity | 1.5 |
| C evaluation harness | 1.5 |
| D positive-class work | 2.5 |
| E model + quantise | 2.0 |
| F on-device KWS | 2.0 |
| G streaming + ASR | 2.0 |
| H demo UI | 2.5 |
| I validation + rehearsal | 1.0 |
| **Total** | **16.5** |

Over the 16 h ceiling, so the declared cut order, worst case first to be dropped:
**E2** (architecture search) then **D5** (RIR/channel sim) then **D4** (SpecAugment).
**Nothing in C or I is cuttable** — those are what make the numbers real.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Positive class too small for speaker-independent detection | **High** | High | Phase D; be explicit in the demo that it is speaker-dependent unless D3/D6 change that |
| Judge speaks the keyword and nothing happens | Medium | High | D3/D6; plus a rehearsed operating point and an on-screen confidence trace so a near-miss is still legible |
| Board unavailable / pin map wrong | Medium | High | 9 h of hardware-free work first; pin map validated against the datasheet table before power-on |
| Wi-Fi unavailable at the venue | Medium | High | Windows Mobile Hotspot fallback; the whole server is local, so no internet is needed |
| ASR too slow on the i3-8100 | Medium | Medium | `tiny.en` fallback, measured in G2 |
| C: fills completely and breaks the toolchain | Medium | High | everything new on E:; monitor free space |
