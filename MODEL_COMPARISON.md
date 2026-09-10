# model-1 vs model-2 — real-device domain adaptation

**Date:** 2026-09-10 · **Experiment:** `BUILD_LOG.md` EXP-007 · **Data:** `data/dataset_v3` (`takshila-demo-2.0`)
**Tool:** `tools/compare_models.py` · **Raw record:** `artifacts/comparison/model_comparison.json`

Both models share the DS-CNN architecture unchanged (10,947 params, 3.29 M MACs).
The only differences are the training data and, at inference, window level
normalisation. Architecture was not implicated by the domain analysis, so it was
not touched.

| | model-1 | model-2 |
|---|---|---|
| training positives | ~1,069 TTS voices only | TTS + **11 real INMP441 utterances** (×6 placements ×4 oversample = 264 clips) |
| real positive padding | digital silence | the recording's **own room tone** |
| held-out test | utterance-disjoint | **session-disjoint** (`S_PILOT_03` quarantined) |
| frozen at | `artifacts/model_1_baseline/` | `artifacts/model_2_domain/` |

Threshold is chosen **per model on validation** (1 % FAR on validation negatives)
and applied unchanged to test. Nothing was swept on test labels.

---

## Results

| metric | model-1 | model-2 |
|---|---:|---:|
| operating threshold (from validation) | 0.906 | 0.963 |
| **real INMP441 clip recall** (n=18) | **0.0 %** | **100.0 %** |
| real clip median score | 0.002 | 0.999 |
| **streaming, raw audio** | **0/15** | **0/15** |
| streaming median peak, raw | 0.002 | 0.324 |
| **streaming, + level normalisation** | **0/15** | **14/15 (93 %)** |
| streaming median peak, normalised | 0.003 | 1.000 |
| near-homophone rejected | 97.3 % | 96.3 % |
| hard negative rejected | 100 % | 100 % |
| speech negative rejected | 100 % | 100 % |
| false accepts / hour (synthetic negative stream) | 4.0 | **20.0** |
| host inference | 7.49 ms/window | 7.58 ms/window |

**Two changes were both necessary and neither was sufficient.** model-1 with
level normalisation still detects 0/15 — normalisation alone does nothing without
real training data. model-2 without normalisation also detects 0/15 — real
training data alone does nothing while the level mismatch stands.

---

## The second finding: a 16 dB train/deploy level mismatch

model-2's clip recall is 100 % while its streaming detection on the *same audio*
was 0/15. That contradiction is the useful part of this experiment.

The dataset factory peak-normalises every positive to −6 dBFS. The streaming path
fed raw audio. Measured on the held-out session:

| | peak level |
|---|---:|
| factory test clips | −2.3 dBFS |
| raw 1 s windows (what streaming sees) | −18.7 dBFS |

Scoring the **same** window both ways:

| construction | median P | detected |
|---|---:|---:|
| 1 s window from the raw recording | 0.304 | 1/14 |
| the same window, normalised to −6 dBFS | **1.000** | **14/14** |
| factory clip (extract + peaknorm + room tone) | 0.998 | 13/14 |
| factory clip **without** peak normalisation | 0.012 | 0/14 |

The model was never broken on real audio. It was being fed real audio 16 dB
below anything it had trained on.

### Why this is cheap to fix

Scaling a waveform by *s* multiplies every mel energy by *s²*, a constant
+2·ln(*s*) offset in log-mel, and an orthonormal DCT-II maps a constant vector
onto **c0 alone**:

```
c0' = c0 + 2·√N_MEL·ln(s)
```

Verified numerically to 4 decimals for gains in [−12, +6] dB. It diverges only
when the scaled signal clips or when mel bins hit `LOG_FLOOR` — the two regimes
the room-tone padding and the level floor exist to avoid.

The consequence for firmware: **normalisation does not force the frame ring to
be recomputed per window.** Frames stay incremental; only c0 is adjusted at
inference. Implemented in `training/features.py` as `level_gain()` /
`apply_level_gain()`, with `StreamingFrontEnd(level_normalise=True)`. Streaming
plumbing verified against the batch path at **0.00e+00** max abs difference.

---

## int8 quantisation

`artifacts/model_2_domain/kws_int8.tflite`, 25,896 bytes.

| criterion | measured | bar | |
|---|---:|---:|---|
| max \|P_float − P_int8\| | 0.0788 | < 0.05 | **FAIL** |
| correlation | 0.99930 | > 0.99 | pass |
| decision flips at 0.5 | 0.298 % (3/1007) | < 1 % | pass |

The parity gate **fails on its max-deviation criterion** and that is reported as
a failure, not relaxed. Its operational cost was then measured rather than
assumed: on the held-out session, streaming detection is **13/15 for both float
and int8**, median peak 1.000 vs 0.996. The divergence is real and does not
change a decision on this data. It should be re-checked when the test set grows.

---

## What this does NOT prove

* **The test set is 3 utterances (18 clips).** A recall measured on it carries
  roughly **±35 pp**. `data/dataset_v3` is marked **PROVISIONAL** by the build
  for exactly this reason. 100 % real clip recall means "no failures in 18
  clips", not "100 % recall".
* **One session, one speaker, one room, one day.** Session effects and domain
  adaptation cannot be separated with a single held-out session.
* **The model is speaker-dependent by decision** (D-015). No speaker-independence
  claim is available from this data, and none is made.
* **The real-device false-alarm rate is unmeasured.** No recording of real
  non-keyword speech on this microphone exists. On 0.4 min of *verified*
  speech-free device audio, model-2 with normalisation produced **1 false accept**
  (max score 0.995) against **0** without. That is a warning flag on a sample far
  too small to rate — the 20 FA/hour above is measured on a synthetic negative
  stream, which is not the same thing.
* An earlier measurement in this session put real-device false accepts at
  1293/hour. It was **wrong and is withdrawn**: the "negative" stream was built
  by excising the keyword using the speech-span detector, which on the 37
  too-quiet takes located only a ~140 ms fragment and left most of a real
  keyword in the stream. It was counting true positives as false accepts.

---

## What to do next

1. **Record real non-keyword speech on this microphone.** It is the largest
   measurement gap: the demo's false-alarm behaviour is currently unmeasurable.
   `tools/record_protocol.py` blocks `neg_ksha`, `neg_taks`, `neg_partial`,
   `neg_speech`.
2. **Record a second held-out session** so the test set is more than 3
   utterances. At ~40 usable positives the confidence interval narrows from
   ±35 pp to about ±15 pp.
3. **Mirror level normalisation in firmware** when the C++ front end is written —
   `LEVEL_NORM_TARGET_DBFS = -6.0`, `LEVEL_NORM_FLOOR_DBFS = -45.0`, applied as
   the c0 offset above.
4. Re-check int8 parity once the test set is large enough for the max-deviation
   figure to mean something.
