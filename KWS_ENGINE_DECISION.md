# KWS_ENGINE_DECISION.md

**Date:** 2026-09-09 · **Status:** decided · **Context:** 12–16 h demo build window
Covers: engine selection · feature/inference pipeline verification · keyword sanity check.

---

## 1. Candidate engines

### A. ESP-SR / WakeNet

| Property | Finding |
|---|---|
| Custom keyword support | **Yes, but not by us.** Espressif offers two routes: their corpus-collection + training service, or TTS-sample training. **Both are paid services.** |
| Self-service training | **Does not exist.** No free self-service path from Espressif; third parties (e.g. CustomESP-SR) also charge. |
| Dataset requirement | **>500 speakers, ≥100 children, ≥20,000 entries**, <40 dB room |
| Turnaround | **2–3 weeks** |
| Framework | ESP-IDF component; we are on **Arduino core 2.0.17 / IDF 4.4** (D-003) |
| Iterate in 12–16 h? | **Impossible — cannot even start.** |

### B. Custom neural KWS via TFLite Micro + ESP-NN

| Property | Finding |
|---|---|
| Custom keyword support | **Total.** We define the classes and train from scratch. |
| Framework | **Arduino-compatible TFLM port + ESP-NN — already installed and pinned** in `firmware/platformio.ini` |
| Measured on this exact board | **84.17 ms/inference, 15,460 B arena, ESP-NN worth 5.48×, MFCC host/device parity at correlation 1.0000000000** `[prior-build]` |
| Licence | TFLM Apache 2.0; `ESP_TF` Arduino port Apache 2.0 |
| Tooling | Keras → `TFLiteConverter` int8 → C array. Smoke-tested working in this repo (OPS-002). |
| Cost to build | Training + feature pipeline must be written — the main risk |

### C. microWakeWord (Apache 2.0)

| Property | Finding |
|---|---|
| Custom keyword support | **Yes, fully self-service and free** |
| Architecture | MixConv mixed depthwise convolutions, **streaming** (keeps internal state, processes one chunk at a time); derived from Google Research's *Streaming keyword spotting on mobile devices* (arXiv 2005.06720) |
| Features | **16 kHz · 30 ms window · 10 ms stride · 40 spectrogram features**, via the `micro_speech` preprocessor **including noise suppression and AGC** |
| Runtime | **TFLite Micro** — same runtime as option B |
| Model | int8 quantized `.tflite`; example manifest declares `tensor_arena_size` **22,860 B** |
| Training data | **Piper TTS sample generator**; pre-computed negative spectrogram feature sets published on Hugging Face |
| Optimises for | **false accepts per hour on ambient background noise** — our exact headline metric |
| Framework fit | Built for **ESPHome / ESP-IDF**. The `.tflite` is portable, but its **feature frontend is not** — NS + AGC would have to be reimplemented bit-exactly on our Arduino stack or host/device parity fails |

---

## 2. Comparison against the required criteria

Scored for **this project, in this window**. 5 = best.

| Criterion | A · WakeNet | B · TFLM+ESP-NN | C · microWakeWord |
|---|---|---|---|
| Custom keyword support | 2 (paid, outsourced) | **5** | **5** |
| Training / customisation path | 1 (2–3 weeks, paid) | 4 (we write it) | **5** (scripted, exists) |
| Dataset requirement | 1 (500 speakers) | **4** | **5** (synthetic-first) |
| ESP32-S3-N16R8 deployment feasibility | 3 (IDF only) | **5** (measured here) | 3 (IDF/ESPHome-shaped) |
| Inference latency | 4 (optimised asm) | **5** (84.17 ms measured) | 4 (streaming, unmeasured here) |
| Accuracy potential | **5** | 4 | 4 |
| False-trigger resistance | **5** (500-speaker corpus) | 3 (data-limited) | 4 (FA/h-optimised, synthetic breadth) |
| Integration complexity | 2 (IDF migration) | **5** (stack already pinned) | 2 (frontend port + NS/AGC parity) |
| Licensing | 3 (paid service) | **5** (Apache 2.0) | **5** (Apache 2.0) |
| Use our `Takshila` keyword | 2 (via paid service) | **5** | **5** |
| Use the real INMP441 input | 4 | **5** | 4 |
| Conversion / deployment tooling | 3 | **5** (smoke-tested here) | 4 |
| **Iterate within 12–16 h** | **0 — impossible** | **4** | 3 |
| **Total** | **31** | **59** | **53** |

---

## 3. Decision — **Option B: custom neural KWS on TFLite Micro + ESP-NN**

### Why B wins

1. **A is not merely worse, it is unavailable.** Custom WakeNet training is a paid Espressif service with a 2–3 week turnaround and a 500-speaker corpus prerequisite. It cannot start today, let alone finish tomorrow. It is eliminated on feasibility, not preference.

2. **B is the only option with measured evidence on this exact board and this exact toolchain.** 84.17 ms/inference, 15,460 B arena, ESP-NN worth a measured 5.48×, and MFCC host/device parity demonstrated at correlation 1.0000000000 `[prior-build]`. Everything else is a projection.

3. **C's cost is in the wrong place for this window.** microWakeWord is genuinely good — Apache 2.0, self-service, streaming, and it optimises for false-accepts-per-hour, which is exactly our metric. But it is built for ESPHome/ESP-IDF, and its `micro_speech` frontend applies **noise suppression and AGC**. Porting that to our Arduino/IDF-4.4 stack bit-exactly is a parity problem, and `DECISIONS.md` D-003 already records that an IDF-5.x migration costs a multi-GB download and hours we do not have. **The risk is concentrated in the last hours before the demo — the worst possible place.**

4. **B keeps the whole pipeline under our control**, which matters because the SIH problem statement grades *false activations* and requires the KWS pipeline be built on open-source TinyML frameworks (C10) with training on a custom keyword (C11). With B, compliance is unambiguous and demonstrable.

### What we take from C anyway

Rejecting C's runtime does not mean rejecting its insight. **Two things are adopted:**

- **Synthetic-first data generation.** Piper TTS sample generation is the proven way to obtain training breadth without speakers, and it is exactly the constraint we face tomorrow. Adopted for **hard negatives without reservation**, and for **positives only under the D-007 A/B gate** — see §6.
- **FA/h as the optimisation target**, not clip accuracy. Already our policy (D-005); microWakeWord's design corroborates it.

### Fallback, declared now

If B's training pipeline stalls past the **T+6 h** checkpoint (§7 of `DEMO_DATASET_SPEC.md`), fall back to **microWakeWord** and accept the frontend-port risk, because a working model on a different runtime beats no model. This is a pre-declared trigger, not a judgement to be made under pressure.

---

## 4. Feature / inference pipeline — verified, not assumed

**The verification finding first:** TFLite Micro imposes **no** feature pipeline. It executes whatever graph it is given. Therefore the 49 × 13 / 25 ms / 20 ms pipeline is **ours to define**, not something an engine dictates — which is precisely why it had to be checked rather than assumed.

microWakeWord's very different choice (**30 ms window, 10 ms stride, 40 spectrogram features, with NS + AGC**) is the proof that these parameters are engine-and-designer decisions. Ours are retained because they carry measured evidence on this board; theirs are noted as a valid alternative.

### The pipeline of record

| # | Property | Value | Source |
|---|---|---|---|
| 1 | **Sampling rate** | **16,000 Hz** | model input; ESP-SR format convention; INMP441 at 64 SCK/frame ⇒ SCK 1.024 MHz. Measured **16,001.60 Hz (+0.010 %)** `[prior-build]`, re-verify in A5 |
| 2 | **Sample format** | **int16 signed LE**, taken as the **upper 16 bits** of the INMP441's 24-bit sample left-justified in a 32-bit I²S slot | INMP441 datasheet; wrong shift = silent 48 dB error (QC-8) |
| 3 | **Channels** | **1 (mono)** — LEFT only, `L/R` tied to GND; right slot discarded | INMP441 datasheet |
| 4 | **Frame / window** | **400 samples = 25 ms**, periodic Hann | `ARCHITECTURE.md` §3 |
| 5 | **Hop / step** | **320 samples = 20 ms ⇒ 50 frames/s** | `ARCHITECTURE.md` §3 |
| 6 | **Feature extraction** | 512-point FFT → power spectrum → **40 mel filters, 125–7500 Hz** → log → **orthonormal DCT-II** → keep **13 MFCC** → per-coefficient mean/std normalisation (**train statistics only**) | `ARCHITECTURE.md` §3 |
| 7 | **Model input tensor** | **`[1, 49, 13, 1]` int8** — 49 frames × 13 MFCC = 1.0 s context | `ARCHITECTURE.md` §3 |
| 8 | **Sliding-window behaviour** | Ring buffer of 49 frames. **One new frame computed per 20 ms hop; no 49-frame recompute.** Oldest frame evicted. | `ARCHITECTURE.md` §2 component 4 |
| 9 | **Smoothing / trigger** | probability threshold → **M-of-N vote** over a sliding history → **refractory lockout**. Operating point swept on SWEEP, reported on VALIDATE. | `ARCHITECTURE.md` §5, D-005 |
| 10 | **Inference cadence** | **Every 10 hops = 200 ms** (not every hop). See below. | derived |

### Inference cadence — the number that is easy to get wrong

Features are computed every **20 ms**, but inference is **not** run every 20 ms. At 84.17 ms/inference `[prior-build]`, 50 inferences/s would need 4.2 s of CPU per second — impossible.

| Cadence | Inferences/s | CPU duty (at 84.17 ms) | Added detection latency |
|---|---|---|---|
| 20 ms (every hop) | 50 | **421 %** — impossible | 0 ms |
| 100 ms | 10 | **84 %** | ≤ 100 ms |
| **200 ms (chosen)** | **5** | **~42 %** (prior measured **48 %** at this cadence) | ≤ 200 ms |
| 500 ms | 2 | 17 % | ≤ 500 ms |

**Phase-1 choice: 200 ms.** It matches the only cadence with a measured CPU figure on this board, and Phase 1 has RAM/CPU explicitly out of scope so the 48 % is a declared, displayed Phase-2 debt (`ARCHITECTURE.md` §9). **100 ms is available as a demo-day latency improvement** if the measured inference time allows.

### ⚠ Verification finding: the 1.0 s window vs slow speech

`RESEARCH_DATASET_ROADMAP.md` §2 records `Takshila` at **700–1000 ms when spoken slowly**. The positive-class rule requires the complete keyword plus **≥ 60 ms margin at each edge** inside the window, so the longest admissible utterance in a 1.0 s window is **880 ms**.

**Utterances slower than 880 ms cannot satisfy the margin rule.** Left unaddressed, they would be labelled `hard_negative/partial` — actively training the model to *reject* slow speech, which is the opposite of what a demo needs when a judge speaks deliberately.

| Option | Effect | Verdict |
|---|---|---|
| Widen window to 1.2 s (60 × 13) | +22 % input ⇒ ~103 ms inference; still inside a 200 ms cadence | **Tier-2 experiment** |
| Keep 1.0 s, cap prompted slow rate at ≤ 850 ms | No architecture change; keeps the measured 84.17 ms evidence | **Tier-1 choice** |
| Relax the margin for slow takes | Reintroduces truncated-onset positives | Rejected |

**Tier-1 decision: keep 49 × 13, and prompt the slow rate as "deliberate, not drawn out", targeting ≤ 850 ms.** Any take measuring > 880 ms is flagged `duration_over_window=true` and excluded from positives rather than silently mislabelled. **This is a known, documented limitation** and the first Tier-2 architecture experiment.

---

## 5. Keyword sanity check — `Takshila`

Deployment-compatibility check only; the selection research is not redone.

| Check | Result |
|---|---|
| Trainable on the selected engine? | ✅ Option B trains from scratch on any keyword — no engine-side vocabulary constraint |
| Fits the 49 × 13 / 1.0 s input? | ✅ at normal (520–780 ms) and fast (380–520 ms) rates. ⚠ **slow rate must be capped at ≤ 850 ms** (§4) |
| Survives the INMP441 channel? | ✅ the /ʃ/ sits at 3–8 kHz, the mic's cleanest band; the part is −3 dB at 60 Hz/15 kHz and 64.6 % of its noise is < 100 Hz, all below the 125 Hz mel floor `[prior-build]` |
| Survives 13-MFCC compression? | ✅ the discriminative events are broad spectral-shape changes (/k/ burst → /ʃ/ frication plateau → /iː/ high-F2), which is what low-order MFCCs represent best |
| Distinguishable at a 200 ms cadence? | ✅ ~600 ms of speech is seen by **≥ 3 consecutive inference windows**, which is what makes M-of-N smoothing viable |
| Collectable in the demo window? | ✅ 3 syllables, unambiguous for Indian speakers, no pronunciation coaching |
| Licensing / branding | ✅ no blocker; "Takshashila Institution" exists as an organisation name — noted, no technical impact |
| Any serious technical reason to change it? | **No.** |

> ## ✅ KEYWORD LOCKED: `Takshila`
> No technical reason to change it was found. `DECISIONS.md` **D-011 stands and is locked.**
> The one caveat is a *window* constraint, not a keyword defect, and it is handled in §4.

---

## 6. Honest position on synthetic speech

The user's instruction is explicit and is adopted as policy: **do not pretend synthetic speech is equivalent to diverse real speakers.**

| Use | Status | Reasoning |
|---|---|---|
| **Hard negatives / near-homophones from TTS** | ✅ **Adopted without reservation** | We need the model to reject *phone sequences*. A synthetic "shiksha" contains the क्ष conjunct genuinely. No claim about speaker realism is required. |
| **Background, silence, unknown speech from public corpora** | ✅ Adopted | Real human speech, correctly licensed |
| **Synthetic positives** | ⚠ **Provisional, A/B-gated** | Trains breadth we cannot otherwise reach in one day, but TTS voices differ from real speech in ways that may not transfer. Ships **only if** a model trained with them beats one without, judged on **real held-out human positives** through the streaming harness (D-007). |
| **Claiming speaker independence from synthetic positives** | ❌ **Forbidden** | Only a speaker-disjoint test split of *real humans* can support that claim. |

**The demo must state its speaker coverage honestly.** With the Tier-1 speaker count (§`DEMO_DATASET_SPEC.md` §2) the system is **speaker-dependent-leaning**, and saying so is better engineering than being caught by a judge whose voice fails.
