# Baseline KWS model — measured results

**Date:** 2026-09-10 · **Keyword:** `Takshila` · **Dataset:** `data/dataset_v2`
**Model:** `artifacts/model/kws_float.keras`, `artifacts/model/kws_int8.tflite`

Every number here was produced by a script in `training/` and is reproducible.
Where a figure was not measured, this document says so.

---

## 0. The headline, stated plainly

**The model classifies synthetic speech well and does not detect the real
speaker at all.**

| | |
|---|---|
| Clip recall, synthetic TTS positives (validation) | **62.0 %** |
| Clip recall, real INMP441 positives (validation) | **20.4 %** |
| Clip recall, real INMP441 positives (**test**) | **0.0 %** — 0 of 54 |
| Streaming detections on real recordings | **0 of 18** |
| Median P(keyword) on real audio | **0.10** |
| Median P(keyword) on synthetic audio | **0.94** |

This is a genuine measured failure, not a tuning problem. It is reported here
rather than buried because it is the single most important fact about the
current build, and because the threshold was deliberately **not** retuned to
manufacture a better-looking number (CLAUDE.md safety rule 3).

---

## 1. What was built

### Dataset — `data/dataset_v2`, leakage gate PASS

| Split | Clips | keyword | unknown | background |
|---|---:|---:|---:|---:|
| train | 16,903 | 3,149 | 11,004 | 2,750 |
| validation | 2,968 | 599 | 2,019 | 350 |
| test | 1,055 | 54 | 1,001 | 0 |

* **Train positives are 100 % synthetic** Piper TTS (~1,069 voices). This is by
  design — D-014 reserves real audio for evaluation.
* **Real INMP441 audio: 18 usable utterances** out of 62 recorded takes, one
  speaker, split 9 / 9 into validation and test, ×6 window placements = 54 + 54.
* Session-disjoint splitting is still **not** achievable: session `S_PILOT_02`
  yields 1 usable take of 30. Session overfitting is **not controlled for**.

### Model — DS-CNN (D-012)

| | |
|---|---|
| Parameters | 10,947 |
| MACs / inference | 3,291,744 |
| Input | 49 × 13 × 1 MFCC |
| Trained | 15 epochs (early stop from 30), 4.7 min |
| Best validation accuracy | 0.9363 |
| Host latency, float Keras | 1.94 ms / clip |
| Host latency, TFLite int8 | 0.38 ms / clip |
| Projected device latency | ~103 ms — *projection from the prior build's single ESP-NN measurement, not a measurement* |

---

## 2. Clip-level results

Threshold **0.900**, selected on the **validation** split by a rule declared
before any test number was looked at: *the lowest threshold whose false-accept
rate is ≤ 1 %*. Applied once to test, unchanged.

### Validation (599 positive / 2,369 negative)

```
TP 349   FN 250   FP 23   TN 2346
precision 0.9382   recall 0.5826 [95% CI 0.543-0.621]   F1 0.7188
FRR 0.4174   FA rate 0.0097   argmax accuracy 0.9363
```

| Subset | n | metric | value | 95 % CI |
|---|---:|---|---:|---|
| positives — real INMP441 | 54 | recall | **0.2037** | 0.118 – 0.329 |
| positives — synthetic TTS | 545 | recall | 0.6202 | 0.579 – 0.660 |
| near_homophone | 609 | correct reject | 0.9754 | 0.960 – 0.985 |
| hard_negative | 286 | correct reject | 0.9720 | 0.946 – 0.986 |
| speech_negative | 1,124 | correct reject | 1.0000 | 0.997 – 1.000 |
| silence | 350 | correct reject | 1.0000 | 0.989 – 1.000 |

### Test (54 positive / 1,001 negative)

```
TP 0   FN 54   FP 10   TN 991
precision 0.0000   recall 0.0000 [95% CI 0.000-0.066]   F1 0.0000
FRR 1.0000   FA rate 0.0100   argmax accuracy 0.9289
```

| Subset | n | metric | value | 95 % CI |
|---|---:|---|---:|---|
| positives — real INMP441 | 54 | recall | **0.0000** | 0.000 – 0.066 |
| near_homophone | 374 | correct reject | 0.9733 | 0.951 – 0.985 |
| hard_negative | 18 | correct reject | 1.0000 | 0.824 – 1.000 |
| speech_negative | 609 | correct reject | 1.0000 | 0.994 – 1.000 |

Confusion at argmax (test) shows the failure is not a threshold artefact — even
with no threshold at all, only **7 of 54** real positives reach the keyword
class:

```
                keyword  unknown  background
  keyword             7       47           0
  unknown            27      973           1
```

**The negative side is genuinely strong.** Speech negatives and silence are
rejected perfectly, and near-homophones — the hardest tier, built specifically
to attack this keyword — are rejected 97.3 %. The model has learned *something*
real. It has just not learned it from audio resembling this microphone.

---

## 3. Streaming results — how the device would actually behave

Sliding 985 ms context, inference every **200 ms**, **2-of-3** smoothing, 1 s
refractory. Threshold 0.900, reused from validation, **not** retuned.

### False accepts, 10 min of continuous TEST negatives

```
2,995 inferences   2 false accepts
12.00 FA / hour    95% CI 1.35 - 43.33  (Poisson, 2 events in 10 min)
```

The interval is wide because 10 minutes is a short observation. The point
estimate alone would overstate what this measurement can support.

### Detection on real recordings containing the keyword

| Session | detected | median peak score |
|---|---|---:|
| S_PILOT | 0 / 14 | 0.103 |
| S_PILOT_02 | 0 / 1 | 0.013 |
| S_PILOT_03 | 0 / 3 | 0.003 |
| **TOTAL** | **0 / 18 (0 %)** | |

**Wake latency: not measurable — nothing was detected.**

---

## 4. Diagnosis — why it fails

Three hypotheses were tested. Two were rejected by measurement.

### Rejected: recording level

Gain applied to the real recordings before streaming, with and without the
`mic_band_limit` channel model:

| gain | 0 dB | +6 | +12 | +18 | +24 | +30 |
|---|---:|---:|---:|---:|---:|---:|
| median peak score | 0.074 | 0.096 | 0.088 | 0.106 | 0.125 | 0.189 |
| detections (of 18) | 0 | 0 | 0 | 0 | 0 | 0 |

Level moves the score in the right direction and nowhere near far enough.

### Rejected: peak normalisation mismatch

The factory builds every positive clip as
`place_in_window(peak_normalize(segment, -6.0), …)`, while the device stream is
never level-normalised. That looked like the obvious culprit. It is not:

| | factory clip (peak-normalised) | identical placement, no normalisation |
|---|---:|---:|
| median score, 18 real utterances | 0.101 | 0.120 |
| number above threshold | 1 | 1 |

Removing the normalisation changes nothing.

### Supported: synthetic-to-real domain gap

Median P(keyword) is **0.94 on synthetic TTS** and **0.10 on real INMP441 audio
of the same word**. Train positives are 100 % Piper TTS. The `mic_band_limit`
channel model plus noise and gain augmentation was intended to bridge that gap
(D-014) and demonstrably does not — augmentation copies information, it does not
add any, and no amount of filtering makes a Piper voice into this speaker on
this microphone.

This is the same class of failure CLAUDE.md records for the prior build, now
measured on the new keyword, the new dataset and a new architecture. It was
predicted; it is now quantified.

---

## 5. TFLite int8 export

```
artifacts/model/kws_int8.tflite    25,896 bytes
input    [1, 49, 13, 1]  int8   scale 0.05587779   zero_point   6
output   [1, 3]          int8   scale 0.00390625   zero_point -128
ops      CONV_2D x4, DEPTHWISE_CONV_2D x3, FULLY_CONNECTED x1, MEAN x1, SOFTMAX x1
```

Fully integer — no float fallback op, so nothing falls off the ESP-NN
accelerated path. Calibrated on 500 seeded TRAIN clips.

### Quantisation parity: **FAIL** against the pre-declared bar

| statistic | measured | bar | verdict |
|---|---:|---:|---|
| max \|P_float − P_int8\| | 0.123786 | < 0.05 | **FAIL** |
| correlation | 0.99816229 | > 0.99 | pass |
| decision flips at 0.900 | 0.19 % (2 of 1,055) | < 1 % | pass |

The two decision-relevant statistics pass; the extreme-value statistic fails.
A single clip near the softmax midpoint can move 0.12 under int8 rounding
without changing any decision, so `max |ΔP|` is arguably the wrong bar for a
softmax output quantised at 1/256.

**That argument is not being used to change the verdict.** The bar was declared
before the run and it failed, so the recorded result is FAIL. Revising the bar
is a decision to be taken explicitly and recorded, not an edit made after seeing
a number one does not like.

---

## 6. Host/device feature parity reference

`artifacts/golden/` — 12 cases, regenerated against the current pipeline.

**Streaming vs batch max abs difference: 0.0 exactly, on all 12 cases.** The
device's frame-at-a-time path and the host's batch path are numerically
identical, so host feature numbers transfer to the device. The firmware parity
bar remains max abs diff < 1e-3 and correlation > 0.9999 against
`golden_reference.h`.

---

## 7. What none of this proves

* No result here is **speaker-independent**. All real audio is one speaker, one
  microphone, one room.
* The negative stream is **concatenated clips**, not naturally continuous room
  audio; the joins are artificial.
* FA/hour rests on a **Poisson count over 10 minutes**, not hours.
* Host latency (1.94 ms float, 0.38 ms int8) says **nothing** about device
  latency. The ~103 ms figure is a projection from one prior-build measurement.
* Quantisation parity is **not** accuracy — it only relates int8 to the float
  model, and the float model does not detect real speech.
* On-device numbers do not exist yet. Nothing has run on the ESP32-S3.

---

## 8. The one change that matters next

The binding constraint is **real positive audio in training**, and it is the
only one of the three hypotheses that survived measurement.

The current design puts all 18 real utterances in validation/test to keep the
evaluation honest. It succeeded: it produced an honest "this does not work".
For a demo that must wake to *this* speaker, the model needs that speaker's
audio in training, and the result must then be labelled **speaker-dependent**.

Concretely, in order of leverage:

1. **Record ~60–100 real takes** with the corrected `tools/record_session.py`,
   which now applies the factory's own acceptance rule live and names the reason
   for each rejection. On the three sessions recorded so far it agrees with the
   factory on **64 of 64** takes. At ~15 s per take that is 15–25 minutes.
   The dominant historical failure — 26 of 30 and 8 of 15 takes rejected as
   **TOO QUIET** — is now reported at record time instead of hours later.
2. **Reserve one whole session as a held-out test set**, which finally makes the
   split session-disjoint, and put the rest in training.
3. **Retrain.** No architecture change; the negative-side results show the model
   and pipeline are sound.

Re-recording is not a workaround for a broken tool this time. The tool is fixed;
the data that exists was captured before it was.
