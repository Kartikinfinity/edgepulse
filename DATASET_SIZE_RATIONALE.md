# DATASET_SIZE_RATIONALE.md

Why the demo dataset is the size it is. **Not** 40,000 samples because that is a round number —
derived from what actually limits this project.

**Date:** 2026-09-10 · **Keyword:** `Takshila` · **Window:** ~12–16 h total build

---

## 1. The binding constraint is diversity, not sample count

A KWS model learns from **distinct acoustic realisations**. Duplicating a realisation with a new
noise seed adds a training example but almost no information. So the ceiling is set by:

| Axis | What we actually have |
|---|---|
| **Distinct TTS voices** | **~1,090** (904 LibriTTS-R + 109 VCTK + 24 L2-ARCTIC + 18 ARCTIC + 9 Marathi + 6 single-speaker Indic) |
| **Distinct human speakers** | **1** |
| Keyword spellings / variants | 4 English romanisations + 5 Indic scripts |
| Synthesis parameters | 4 length scales × 3 noise scales × 3 noise-w = 36 combinations |
| Real recordings that pass QC | **14** (of 17 pilot takes) |
| Real background sources | 6 Speech Commands + 2 own INMP441 room tone |

**Past ~6 renderings per voice the marginal information approaches zero** — the same synthesiser,
same speaker embedding, same text, differing only in prosody noise. That is the number that sets
the positive count, not a target chosen in advance.

## 2. Positives

```
~900 distinct voices  ×  ~6 renderings each  ≈  5,400 TTS positives
```

Why ~6 and not 20: renderings 7–20 vary only `noise_scale`/`noise_w`, which perturbs prosody
within one voice. Cheap to generate, but it inflates the count without widening the acoustic
distribution — precisely the mistake that made a 21,267-clip predecessor corpus behave like the
110 utterances it actually contained.

**Real positives: 14 recordings × 6 window offsets ≈ 84 clips.** These are **not** training data.
They are the entire honest evaluation signal, so they go to validation and test only.

## 3. Positive : negative ratio

KWS is an extreme-imbalance problem in deployment: the device hears the keyword for perhaps
1 second per hour. Training at 1:1 produces a trigger-happy model.

| Ratio | Effect |
|---|---|
| 1:1 | high recall, unusable false-alarm rate |
| **1:3** | **chosen** — enough negative pressure to shape the boundary, still trainable without heavy reweighting |
| 1:10+ | better FA in principle, but the positive gradient signal gets thin on a small model, and epochs get slow on CPU |

**1:3 in the data**, with `negative_class_weight` available at training time as the finer control
(microWakeWord's documented lever for cutting false accepts). Data ratio and loss weighting are
independent knobs; fixing the data at 1:3 leaves the second one free.

## 4. Hard negatives — sized by the confusable inventory

74 confusable phrases (`KEYWORD_SELECTION.md` §13, tiers क्ष / taks / ʃiːl / neighbour / boundary).

```
74 phrases × ~57 voice renderings each ≈ 4,200 near-homophones
```

These carry more information per clip than any other negative class, because FakeWake shows false
accepts concentrate on **shared phonetic snippets**. A generic English word exercises the wrong
part of the boundary; *shiksha* exercises exactly the right part.

**Partial-keyword negatives: ~2,200**, cut from the positives themselves at 25–85 % coverage.
This is the single highest-value negative class and it is not optional: without it a predecessor
model fired on **49.7 %** of realistic sliding windows while its curated clip set reported
**10.7 %**.

## 5. Unknown speech, background, silence

| Class | Count | Why that number |
|---|---:|---|
| `speech_negative` | **8,000** | 36 Speech Commands word classes × ~220 clips. Real human speech from thousands of speakers, CC BY 4.0, already on disk. This is the cheapest real diversity available and it dominates the negative mass. |
| `background` | **2,400** | 6 Speech Commands noise sources, heavily cropped and augmented. Enough to cover the idle condition without letting 6 sources dominate. |
| `silence` | **700** | Real INMP441 room tone. Small on purpose: silence is trivially separable and over-representing it wastes capacity. |

## 6. Total, and the sanity check against compute

| Class | Target |
|---|---:|
| `positive` (TTS) | 5,400 |
| `positive` (real INMP441) | ~84 |
| `near_homophone` | 4,200 |
| `hard_negative/partial` | 2,200 |
| `speech_negative` | 8,000 |
| `background` | 2,400 |
| `silence` | 700 |
| **Total** | **≈ 23,000 clips ≈ 6.4 h of audio ≈ 740 MB** |

**Compute check** — the reason this is not larger:

| Stage | Cost at 23,000 clips |
|---|---|
| TTS synthesis | ~9,600 calls, ~35 min (one-time, cacheable) |
| Feature extraction (49×13 MFCC) | ~23,000 × 637 floats ≈ 59 MB, a few minutes |
| One training epoch, small DS-CNN, **CPU-only i3-8100** | ~1–2 min |
| 25 epochs | **~30–50 min** |

At 40,000 clips training would take ~1.5 h per run inside a 12–16 h window that also has to
cover firmware, server and UI. **The size is set by the number of training iterations we can
afford, not by how much data we could theoretically make.** Two or three honest training runs
beat one big one.

## 7. Test-set size and what it can actually resolve

This is the number that limits every claim we make.

| Quantity | Value |
|---|---|
| Real recordings passing QC | **14** |
| Split across validation / test | ~7 each |
| Test positive **clips** (7 × 6 offsets) | **~42** |
| **Independent utterances behind them** | **~7** |

**The honest denominator is 7, not 42.** Six window offsets of one utterance are six views of one
event, not six trials. At n≈7 the 95 % confidence interval on a detection rate is roughly
**±35 pp** — this test set can distinguish "works" from "does not work" and essentially nothing
finer.

For comparison: the deprecated corpus had 17 test utterances (±20 pp) and
`RESEARCH_DATASET_ROADMAP.md` targets 240 (±3.8 pp).

**Consequence, stated before any result is produced:** the headline demo number must come from
the **continuous-audio** evaluation (false alarms per hour over a long negative stream), where
the denominator is time rather than utterance count. Clip-level detection rate from 7 utterances
is a smoke test, not a metric.

## 8. What would move the needle, in priority order

| Action | Cost | Effect |
|---|---|---|
| **+30 real `Takshila` utterances** from the same speaker, fresh session | ~8 min | Test n 7 → ~20, CI ±35 pp → ~±21 pp |
| **+2 more human speakers** × 20 utterances | ~25 min | First genuine cross-speaker evidence; still no independence claim |
| +2 h continuous keyword-free INMP441 audio | unattended | Makes FA/hour measurable at all |
| More TTS renderings per voice | free | **~nothing** — this is the axis already saturated |

The last row is the point of this document: the cheapest thing to add is the thing that helps
least.
