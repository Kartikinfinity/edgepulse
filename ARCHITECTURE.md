# ARCHITECTURE.md

Baseline: the two supplied story documents (`the whole story.pdf`, `major story.pdf`),
`sih_2026_kartik_v.1.pdf`, and `Low_Latency_Efficient_Voice_Activator_Implementation_Plan.pdf`.
Deviations are listed in section 8 with justification, as required.

**Phase-1 scope note.** The SIH constraints of <256 KB RAM and <10 % idle CPU are
**deliberately out of scope** for this build, by instruction. They are *not* deleted from the
problem — section 9 records what we will owe Phase 2, and the system is instrumented to report
both numbers honestly on the dashboard rather than hide them.

---

## 1. End-to-end system

```
                            ESP32-S3-WROOM-1-N16R8
  +----------------------------------------------------------------------+
  |  CORE 0                          |  CORE 1                           |
  |  +----------------------------+  |  +-----------------------------+  |
  |  | I2S + DMA capture task     |  |  | Feature + KWS task          |  |
  |  | 16 kHz / 16-bit / mono     |--|->| 25 ms frame, 20 ms hop      |  |
  |  | -> PCM ring buffer         |  |  | 40-mel -> 13 MFCC           |  |
  |  |    (2.0 s, PSRAM)          |  |  | -> 49x13 int8 DS-CNN        |  |
  |  +----------------------------+  |  |    (TFLM + ESP-NN)          |  |
  |                                  |  +--------------+--------------+  |
  |                                  |                 v                 |
  |                                  |  +-----------------------------+  |
  |                                  |  | VAD gate + M-of-N vote      |  |
  |                                  |  | + refractory  -> WAKE       |  |
  |                                  |  +--------------+--------------+  |
  |  +-------------------------------+-----------------v--------------+  |
  |  | CORE 1: streamer task - pre-roll from ring + live PCM          |  |
  |  | WebSocket binary frames + JSON telemetry                       |  |
  |  +--------------------------------+-------------------------------+  |
  +-----------------------------------|----------------------------------+
                                      | Wi-Fi 2.4 GHz
                                      v
             +---------------------------------------------+
             |  SERVER (host PC, 192.168.1.2)              |
             |  ws://:8765  audio in  --> ASR              |
             |    faster-whisper (CTranslate2, int8, CPU)  |
             |        |                                    |
             |        v                                    |
             |  transcript --> intent parser --> action    |
             |        |                                    |
             |        v                                    |
             |  ws://:8080  --> live dashboard (browser)   |
             +---------------------------------------------+
```

## 2. Seven software components (mirrors the story document's list)

| # | Component | Where | Notes |
|---|---|---|---|
| 1 | Audio capture | Core 0, I2S + DMA | legacy `driver/i2s.h` (IDF 4.4) |
| 2 | PCM ring buffer | PSRAM, 2.0 s | large because Phase 1 has RAM headroom; gives generous pre-roll |
| 3 | VAD | Core 1 | band-limited energy + adaptive floor. **Indicator first, gate second** (section 4) |
| 4 | Feature extraction | Core 1 | streaming: one 25 ms frame per 20 ms hop, never a 49-frame recompute |
| 5 | KWS model | Core 1 | int8 DS-CNN via TFLM + ESP-NN |
| 6 | Decision / state machine | Core 1 | `INIT -> LISTENING -> WAKE -> STREAMING -> LISTENING` |
| 7 | Audio streamer | Core 1 | WebSocket binary PCM16 + pre-roll |

## 3. Audio front end

| Parameter | Value | Rationale |
|---|---|---|
| Sample rate | 16 kHz | dataset is 16 kHz; no resampling anywhere |
| Format | 24-bit in 32-bit I2S slot, upper 16 bits kept | INMP441 native format |
| Channel | LEFT (`L/R` to GND) | [datasheet] |
| Frame | 400 samples (25 ms) | |
| Hop | 320 samples (20 ms) | 50 frames/s |
| FFT | 512-point, periodic Hann | |
| Mel | 40 triangular filters, 125 - 7500 Hz | 125 Hz floor rejects the measured sub-100 Hz drift |
| Output | **13 MFCC** (orthonormal DCT-II of log-mel) | |
| Model input | **49 x 13** = 1.0 s context | matches dataset clip length exactly |
| Normalisation | per-coefficient mean/std, emitted into a generated header | a single global mean/std collapsed c2..c12 and training degenerated `[prior-build]` |

**Non-negotiable:** a host/device parity test must pass (max abs diff and correlation
reported) before any on-device accuracy claim. The prior build reached max abs diff
0.000112 / correlation 1.0000000000 on this exact pipeline `[prior-build]`.

**Front-end sizing is a measured decision, not an assumption.** The prior build measured
a 98x40 log-mel input at **2,240 ms/inference** even with ESP-NN, versus **84.17 ms** for
49x13 MFCC — a 26.6x difference driven almost entirely by input size `[prior-build]`.
Phase 1 lifts the RAM/CPU limits but **not** the real-time limit: inference must still
finish inside the hop. Phase B benchmarks 49x13 / 49x20 / 49x40 on hardware and picks on
measured accuracy-per-millisecond.

## 4. VAD — deliberately not a hard gate by default

The story documents place VAD before KWS to save CPU. Phase 1 does not need that saving, and
`DATASET.md` section 6 measured that **band energy barely separates this data** (speech-band
fraction: positive 0.561, background 0.538). A tight energy gate would therefore drop real
keywords for no benefit.

**Design:** VAD runs and is *displayed* on the dashboard (it is part of the SIH story and is
genuinely useful to show), but by default it only **gates the streaming end-of-utterance
decision**, not the KWS path. A `VAD_GATES_KWS` build flag enables the classic power-saving
behaviour for Phase-2 measurements. This is deviation **A-2** (section 8).

## 5. Decision logic

`threshold` + **M-of-N vote** + **refractory window**. The prior build measured that
N-consecutive is brittle (one dip discards a confident detection) while M-of-N tolerates it,
and — importantly — that two different smoothing rules gave **identical** hardware results:
*decision logic moves along the frontier, it does not create detection capability*
`[prior-build]`. The operating point is chosen from a **streaming** sweep and then
**validated on fresh audio that was not used for the sweep**.

## 6. Post-detection path

| Stage | Design |
|---|---|
| Keyword-end timestamp | latched on the device at the deciding frame; this is *t0* for the latency metric |
| Pre-roll | 500 ms from the ring buffer, so the command's onset is never clipped |
| Transport | **WebSocket, binary PCM16 frames** (~20 ms each), one persistent connection kept open in LISTENING so no TCP/WS handshake is on the critical path |
| End of utterance | device-side silence detector (VAD closed for ~800 ms) with an 8 s cap; server can also close |
| ASR | **faster-whisper** (CTranslate2, MIT) `base.en`, int8, CPU. Fallback `tiny.en` if the i3-8100 cannot keep the demo snappy — measured, not assumed |
| Intent | rule-based parser over the transcript producing `{intent, slots, confidence}` |
| Action | executed and echoed back to the device over the same socket (e.g. LED), closing the loop visibly |

**Latency instrumentation.** Device and server exchange a clock-offset handshake at connect.
Reported separately: KWS inference time; detection to first packet sent; first packet to
server received; server received to ASR first token; to ASR final; to action. The SIH metric
("keyword ending to cloud ASR receiving the audio stream") is the third of these and is
displayed as its own headline number.

## 7. Demo UI — a first-class deliverable

A browser dashboard served by the same host, fed by a WebSocket. It must make the pipeline
legible to a non-technical judge **and** show bad numbers honestly.

**Layout: the pipeline as a live flow diagram**, each stage a node that lights as data passes,
with a panel per stage:

| Panel | Contents |
|---|---|
| Microphone | live waveform + level meter, sample rate, clipping counter |
| VAD | open/closed indicator, band energy vs adaptive floor |
| KWS | **rolling confidence chart with the threshold drawn on it**, per-class probabilities, wake flashes on the timeline |
| Wake event | large state badge: LISTENING / WAKE / STREAMING |
| Capture | pre-roll + live bytes streamed, duration |
| Network | Wi-Fi RSSI, connection state, packets, drops, reconnects |
| ASR | model, state (idle/decoding), decode time, **live transcript** |
| Action | matched intent, slots, executed action, success/failure |
| Latency | the breakdown of section 6 as a stacked bar, plus the headline end-to-end figure |
| Resources | ESP32 CPU % per core, internal SRAM free, PSRAM free, tensor arena bytes, model bytes, server CPU |
| Health | uptime, error counters, last error text |
| Timeline | scrolling event log with timestamps, exportable |

Design rules: no fabricated values — a stage with no measurement shows "not measured";
failures render red and stay on the timeline rather than being cleared.

## 8. Deviations from the supplied architecture

| # | Deviation | Justification | Preserves SIH objective? |
|---|---|---|---|
| **A-1** | ASR server is a **host on the LAN**, not an internet cloud service | The problem statement requires a *remote ASR server*, and a LAN server is remote from the MCU. Every open-source ASR runs locally anyway; commercial cloud ASR would breach the "open-source only / no proprietary SDK" restriction. It also removes internet dependence from a live demo. A `SERVER_URI` config still allows a real remote endpoint. | Yes — the edge/cloud split is intact |
| **A-2** | VAD does not gate KWS by default | Measured: band energy barely separates this dataset (`DATASET.md` section 6), so gating costs detections and buys CPU we are told to ignore in Phase 1. Retained behind a flag for Phase 2. | Yes — VAD is implemented, shown, and measurable |
| **A-3** | Ring buffer in **PSRAM at 2.0 s** rather than a minimal SRAM buffer | Phase 1 has RAM headroom; a longer pre-roll strictly improves ASR quality. | Yes |
| **A-4** | Streaming is **raw PCM16, not Opus** | The plan lists Opus as optional under bandwidth pressure. On a LAN, 256 kbit/s is free, and an encoder adds latency, CPU and a failure mode to a live demo. Bandwidth is not a graded metric; latency is. | Yes — "minimal data overhead" is met by streaming only after detection |
| **A-5** | Toolchain stays **Arduino core 2.0.17 / ESP-IDF 4.4** | See `DECISIONS.md` D-003 — it is the only stack with measured on-hardware evidence in this project (84 ms inference with ESP-NN). | Yes |
| **A-6** | Headline accuracy is reported from a **streaming simulation**, not clip accuracy | The prior build's clip metrics were optimistic by 4.6x (false-fire) and ~12x (rate). `DATASET.md` section 7. | Yes — it makes the SIH accuracy metric meaningful |
| **A-7** | **Synthetic (TTS) positives** proposed as a training augmentation | The one real lever on the 110-utterance / one-speaker ceiling. Open-source TTS only. Gated by an A/B experiment on real held-out positives — it ships only if it measurably helps. | Yes — no pre-trained *keyword* model is used; only synthetic audio for a custom keyword |
| **A-8** | An **intent/action stage** after ASR | The problem statement stops at ASR; the story documents show `TEXT -> action`. Included because the demo needs a visible outcome. Kept thin and rule-based. | Yes — additive |

## 9. What Phase 2 will owe (recorded now, not forgotten)

- Idle CPU < 10 %: the prior build measured **48 %** of one core at a 200 ms cadence
  `[prior-build]`. Levers: VAD gating (A-2 flag), longer hop, smaller input, ESP-DSP FFT,
  and cutting inference cadence when VAD is closed.
- RAM < 256 KB: prior firmware used 72,924 B plus a 15,460 B arena `[prior-build]`, i.e.
  already inside budget — but the PSRAM ring buffer (A-3) and Wi-Fi/TLS buffers must be counted.
- Both numbers are shown live on the dashboard from day one so the Phase-2 gap is never a surprise.
