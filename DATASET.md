# DATASET.md — `solvani_kws_release`

Everything below was **measured in this tree on 2026-09-09** with
`tools/analyze_manifests.py` and `tools/audio_probe.py`, unless marked otherwise.

Location: `E:\sih2026\data\solvani_kws_release`
Provenance: `sih 2026 2.0\training Dataset (don't open)-20260908T164308Z-1-001.zip`
→ nested `solvani_kws_release.zip` (570.5 MB, 42,628 entries).

---

## 1. What it is

Keyword: **`solvani`** (*sol-vaa-nee*). Two prebuilt variants, both shipped:

| | `dataset_balanced` | `dataset_full` |
|---|---:|---:|
| Clips | **4,084** | **17,183** |
| Manifest rows | 4,084 | 17,183 |
| Files present on disk | ✅ all, 0 missing | ✅ all, 0 missing |

Total WAVs on disk across both: **21,267**.

**Clip format — verified on a random sample of 1,500 files, 100 % uniform:**
mono · 16,000 Hz · 16-bit PCM · exactly **16,000 frames = 1.000 s**. No exceptions found.

Labels: `positive` (contains *solvani*) · `negative` (speech without the keyword) ·
`background` (noise / silence / ambience).

## 2. Split × class

**`dataset_full`**

| split | total | positive | negative | background |
|---|---:|---:|---:|---:|
| train | 15,039 | 693 | 6,849 | 7,497 |
| validation | 1,785 | 80 | 815 | 890 |
| **test** | **359** | **17** | 163 | 179 |

**`dataset_balanced`**

| split | total | positive | negative | background |
|---|---:|---:|---:|---:|
| train | 3,255 | 693 | 1,386 | 1,176 |
| validation | 629 | 80 | 297 | 252 |
| **test** | **200** | **17** | 99 | 84 |

The positive clips are **identical in both variants**; `balanced` only shrinks the
negative/background multiplicity.

## 3. ⚠ The binding constraint — unique source recordings

Augmented copies share a `source_id`. Counting **unique underlying recordings**, not clips:

| label | clips | **unique recordings** | inflation |
|---|---:|---:|---:|
| positive | 790 | **110** | ×7.2 |
| negative | 7,827 | 1,087 | ×7.2 |
| background | 8,566 | 1,190 | ×7.2 |

Positives by split — **unique recordings**:

| split | clips | unique recordings |
|---|---:|---:|
| train | 693 | **77** |
| validation | 80 | **16** |
| **test** | **17** | **17** |

### What that means

- The entire positive class is **110 utterances**.
- **Speaker distribution for positives: `speaker_01` — 100 %.** One person.
- **Environments: 2** — `fan` (60 recordings) and `classroom` (50 recordings), varied distance.
- The test set contains **17 positive utterances**. A detection rate measured on it has a
  95 % confidence interval of roughly **±20 percentage points**. It cannot settle anything
  on its own; the streaming evaluation in §7 is the real bar.

This is the same asymmetry that ended the prior build: thousands of negative speakers
against one positive speaker. See `DECISIONS.md` **D-004**.

## 4. Leakage — checked, and it passes

| Test | Result |
|---|---|
| `source_id` appearing in more than one split | **0 / 2,387** |
| `original_source` (raw recording) in more than one split | **0 / 2,387** |

Augmented variants never straddle a split boundary. The split is genuinely
**recording-disjoint**. It is **not** speaker-disjoint for positives, and cannot be — there
is only one positive speaker. **No result from this dataset may be called speaker-independent.**

## 5. Sources and augmentation

**`dataset_full` source distribution:** librispeech 4,300 · musan 4,352 · esc50 3,544 ·
speech_commands 3,079 · user 1,834 · tts_hard_neg 74.

| label | composition |
|---|---|
| positive | `user` 790 (all `speaker_01`) |
| negative | librispeech 4,300 · speech_commands 3,079 · user 374 (50 unique) · **tts_hard_neg 74** |
| background | musan 4,352 · esc50 3,544 · user 670 (90 unique: "classroom noise", "room with fan") |

**Phonetic hard negatives (`tts_hard_neg`) — only 10 unique phrases:**
`sovani`, `solvaniya`, `silvany`, `sylvani`, `salwani`, `silvani`, `solvanee` *(train)*;
`so many`, `sol vani` *(validation)*; `solvany` *(test)*.
Note the training split never sees `so many` / `sol vani` / `solvany` — the three hardest.
**Expanding this set is cheap and high-value** (`BUILD_PLAN.md` Phase D).

**Augmentations already applied** (per clip, one each): `none` 2,387 · noise at SNR
0/5/10/15/20 dB · `gain_±3/±6 dB` · `pitch_up`/`pitch_down` · `speed_0.95`/`1.05` ·
`reverb` · `filter`. Every one of the 110 positive `source_id`s has an unaugmented `none`
clip, so the clean originals are recoverable.

**Not present:** measured room impulse responses, INMP441 channel simulation, codec
artefacts, SpecAugment (feature-domain), and **time-shift** (see §6).

## 6. Where the keyword sits inside the 1.0 s window

Measured on the 110 unaugmented positives, 300–3400 Hz band energy in 50 ms bins:

- active span ≈ **545 ms**, mean lead-in 235 ms, mean trail-out 221 ms
- peak-energy bin: mean 10.2 / 20, **std 5.1 bins (±255 ms)**
- peak-bin histogram is close to uniform across the whole second

**Conclusion:** the keyword is *loosely* centred with genuine positional spread — better than
a tightly centred corpus, but the spread is a by-product, not a designed augmentation. Broadband
RMS cannot localise the word at all (fan/classroom noise fills the window), which is itself a
useful fact: **an energy-only VAD will not discriminate here.**

Other measurements: 4 of 110 unaugmented positives contain at least one full-scale sample
(mild clipping); RMS across positives 0.034 – 0.485, mean 0.131.
Speech-band (300–3400 Hz) energy fraction: positive 0.561 · negative 0.662 · **background 0.538**
— background is *not* spectrally quiet (ESC-50/MUSAN include music and broadband noise), so
band-energy alone separates almost nothing.

## 7. How this dataset must and must not be used

**The trap, stated plainly.** Every clip is a 1.0 s window that already contains the whole
word. The device sees a window every ~100–200 ms, most of which contain a *fragment* of a
word, or the tail of one and the head of the next. The prior build measured its deployed model
firing on **49.7 %** of realistic sliding windows while its clip test set reported **10.7 %** —
a 4.6× optimism, and later a **~12×** optimism on false-activation rate. `[prior-build]`

**Therefore, mandatory in this build:**

1. **Train with random time-shift**, rolling the keyword across the window including partial
   presentations, and mint explicit **partial-keyword negatives** (word ≥50 % outside the frame).
2. **Report the headline metric from a streaming simulation**: concatenate held-out clips into
   long continuous audio with realistic gaps, slide the real inference window across it, apply
   the real smoothing rule, and count **detections per spoken keyword** and
   **false activations per hour**. Clip accuracy may be reported as a secondary diagnostic only.
3. Hold the *unaugmented* test positives out of every fitting decision, threshold sweeps included.

## 8. Which variant to train on

Start on **`dataset_full`** for negatives/background (more negative diversity is free — the
positives are identical) while keeping class weighting explicit, and use `dataset_balanced`
as the fast iteration loop. Decide by measurement, record in `BUILD_LOG.md`.

## 9. Not available

The release README refers to a rebuild tree at `Desktop/data/` holding the **raw uncut
recordings** and build scripts. **It does not exist on this machine** (checked). Consequences:

- We cannot re-cut the positives at different offsets from the source sessions.
- We cannot extend the 1.0 s window (e.g. to 1.2 s of context) for the existing positives.
- Any new positive audio must be **newly recorded or synthesised**.

If the user can supply that tree, several Phase-D options get materially better.
