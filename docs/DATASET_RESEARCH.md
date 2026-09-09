# DATASET_RESEARCH.md — building a custom-keyword KWS dataset with one human speaker

**Date:** 2026-09-10 · **Keyword:** `Takshila` (locked, D-011) · **Engine:** TFLM + ESP-NN (D-012)
**Constraint that drives everything here:** **one available human speaker, ~12–16 h total build.**

Research done before writing the generator. Findings are filtered for *this* project — where a
published recipe does not transfer, that is stated rather than copied.

---

## 1. The problem this research has to solve

`DEMO_DATASET_SPEC.md` assumed 6 speakers. We have **one**. That is not a smaller version of the
same problem — it changes which techniques are viable:

| Technique | With 6+ speakers | With 1 speaker |
|---|---|---|
| Real positives | primary source | **~100 utterances max, all one voice** |
| Speaker-disjoint split | achievable | **impossible for real audio** |
| Synthetic positives | optional (D-007, A/B-gated) | **the only route to voice diversity** |
| Speaker-independence claim | measurable | **forbidden** |

So the research question is narrow: **what is the strongest defensible way to get voice
diversity without speakers, and how must it be evaluated so the result is not self-deception?**

## 2. Speech Commands methodology — what transfers

Warden's *Speech Commands* (arXiv 1804.03209) is the reference design for small-footprint KWS.
Four things transfer directly:

1. **A dedicated "unknown words" class**, not just keyword-vs-silence. Words *phonetically near*
   the target are the ones that matter.
2. **A `_background_noise_` class** shipped with the corpus and mixed at training time. Our copy
   on disk has 6 files (`doing_the_dishes`, `dude_miaowing`, `exercise_bike`, `pink_noise`,
   `running_tap`, `white_noise`).
3. **Hash-based partitioning by speaker/utterance** so augmented variants cannot cross splits —
   the same principle as our `source_utterance_id` rule.
4. **1-second clips at 16 kHz**, which is why our 49×13 / 1.0 s window is conventional rather
   than arbitrary.

**What does not transfer:** Speech Commands has ~2,600 speakers per word. We cannot imitate its
*scale*; we can only imitate its *structure*.

## 3. microWakeWord's strategy — the closest precedent

microWakeWord (Apache 2.0) is the only mainstream project solving exactly our problem: **train a
custom wake word with no speaker corpus at all.** Its approach:

| Element | microWakeWord | Our position |
|---|---|---|
| Positives | **generated entirely by Piper TTS** (`piper-sample-generator`) | **Adopted**, plus real human positives it does not have |
| Negatives | pre-computed spectrogram features on HuggingFace | **Rejected** — those are 40-feature/30 ms/10 ms spectrograms for *their* frontend, incompatible with our 49×13 MFCC. We generate our own from raw audio. |
| Augmentation | SpecAugment + background mixing | Adopted |
| Optimisation target | **false accepts per hour on ambient background** | Already our policy (D-005) |
| Class weighting | `positive_class_weight` / `negative_class_weight`, raising the negative weight to cut false accepts | **Noted for training** |
| Honest caveat | *"Training a model that works well is still very difficult… This notebook will produce a model, but it will most likely not be usable!"* | Taken seriously — see §9 |

**No published sample counts.** The README gives none, and the search for them returned none.
So our dataset size is derived from first principles in `DATASET_SIZE_RATIONALE.md`, not copied.

## 4. Synthetic TTS for KWS — what is defensible

The literature and practice support TTS positives **as a training-set device**, with two
conditions that this project adopts as rules:

1. **Evaluate on real speech.** A model validated on TTS has only been shown to recognise TTS.
   Our test split is **real human INMP441 audio only**.
2. **Do not claim speaker independence from synthetic voices.** TTS voices are not speakers.

**Domain gap.** TTS output is clean, close-miked, studio-band, and lacks the INMP441's channel,
the room, and real vocal effort variation. Mitigations, in order of value:
- **Band-limit and channel-match** synthetic audio toward the INMP441 response
- **Convolve with room impulse responses** (OpenSLR-28, Apache 2.0)
- **Mix real recorded background** captured on the actual device, in the actual room
- **Keep real human audio for validation and test**, so the gap is *measured*, not assumed

## 5. Voice inventory actually available — the decisive finding

Piper voices (`rhasspy/piper-voices`, MIT-licensed models; engine GPL-3.0) include
**multi-speaker models**, which changes what is reachable in one evening:

| Model | Speakers | Size | Why it matters here |
|---|---:|---:|---|
| `en_US-libritts_r-medium` | **904** | 78.6 MB | bulk voice diversity |
| `en_GB-vctk-medium` | 109 | 77.0 MB | British/varied English |
| **`en_US-l2arctic-medium`** | **24** | 76.8 MB | **L2-ARCTIC = NON-NATIVE English speakers, including Hindi-L1 — Indian-accented English, our actual target population** |
| `en_US-arctic-medium` | 18 | 76.8 MB | additional US voices |
| `mr_IN-google-medium` | 9 | 76.8 MB | Marathi |
| `hi_IN-pratham/priyamvada/rohan` | 3 × 1 | 63.5 MB ea | **native Hindi — renders क्ष correctly** |
| `te_IN-maya`, `ml_IN-arjun` | 2 × 1 | 63 MB ea | Telugu, Malayalam |

**≈ 1,090 distinct synthetic voices for ~600 MB.**

Two of these are specifically valuable for **this** keyword:

- **L2-ARCTIC voices** are non-native English speakers. `Takshila` will be spoken by Indian
  English speakers at the demo, and this is the closest synthetic proxy that exists.
- **Indic-language voices** natively realise the **क्ष conjunct** in *Takshashila*. An en_US voice
  given "Takshila" produces an anglicised /tæk.sɪ.lə/ — which is variant **V7**, useful but not
  the canonical form. Hindi/Telugu/Marathi voices produce the canonical /t̪əkˈʃiː.laː/.

**Locally installed alternative, rejected as primary:** Windows SAPI has only **2 voices**
(David, Zira, both US English). Useful as two extra "voices", not as a strategy.

## 6. Hard-negative generation — why random words are wrong

Per FakeWake (arXiv 2109.09958), false accepts concentrate on **shared phonetic snippets**, and
**Levenshtein distance fails to predict them**. Random English words are therefore close to
useless as hard negatives — they exercise the wrong part of the decision boundary.

The confusable inventory for `Takshila` was derived in `KEYWORD_SELECTION.md` §13 and stands:

| Tier | Basis | Example |
|---|---|---|
| 1 | **क्ष family** — the decisive middle | *shiksha, raksha, lakshya, moksha* |
| 2 | **/tæks/ onset family** | *taxi, tax, tactical, taxonomy* |
| 3 | stressed **/ʃiːl/** nucleus | *Sheila, she'll, shield* |
| 4 | full-word neighbours | *Takshak, Takshashila, Taxila* |
| 5 | cross-word boundary reconstructions | *"talk she'll ah"*, *"attack shield"* |
| **6** | **partial-keyword windows** | 25–99 % of a real utterance |

Tier 6 is not spoken — it is **cut from real positives** and is the highest-value negative class
(a predecessor fired on **49.7 %** of sliding windows without it, vs **10.7 %** on its clip set).

**Generation method:** synthesise Tiers 1–5 across many TTS voices. Synthetic is *fully
appropriate* here — we need the model to reject a **phone sequence**, and a TTS *shiksha*
contains क्ष genuinely. No claim about speaker realism is required.

## 7. Negative / background sources — licence-checked

| Source | Licence | Commercial | On disk? | Use |
|---|---|---|---|---|
| **Google Speech Commands v0.02** | **CC BY 4.0** | ✅ | ✅ `D:\speech_commands`, 36 labels + `_background_noise_` | unknown speech, background |
| MUSAN | CC / US public domain, curated commercial-safe | ✅ | ✗ | music, noise, babble |
| LibriSpeech | CC BY 4.0 | ✅ | ✗ | read English |
| Mozilla Common Voice | **CC0** | ✅ | ✗ | accented / Indic speech |
| OpenSLR-28 RIRs | Apache 2.0 | ✅ | ✗ | reverb |
| Piper voice models | MIT (models); engine GPL-3.0 | ✅ models | downloading | positives, hard negatives |
| **ESC-50** | **CC BY-NC 3.0** | ❌ | — | **EXCLUDED — non-commercial** |
| **Own INMP441 recordings** | project-owned | ✅ | ✅ | real positives, room tone, test |

**Speech Commands being already on disk is the single biggest time saver available** — 36 word
classes of real human speech from thousands of speakers, correctly licensed, no download.

## 8. Augmentation — deployment-realistic, not exhaustive

Applying every augmentation to every sample manufactures a distribution that does not occur.
Design the *distribution* instead:

| Dimension | Range | Applies to | Rationale |
|---|---|---|---|
| Additive noise | SNR 0–30 dB, weighted toward 10–25 | positives, hard negatives | measured pilot room SNR was ~13–33 dB post-HPF |
| Gain | −12…+6 dB | all | distance/effort proxy |
| RIR convolution | RT60 0.2–1.0 s | positives, hard negatives | rooms E1–E3 |
| **INMP441 band-limit** | −3 dB @ 60 Hz / 15 kHz + 125 Hz floor | **all synthetic + public audio** | **the domain-adaptation step** |
| Time shift / offset | uniform across the admissible window | **all splits** | *sampling*, not augmentation |
| Speed | 0.9–1.1×, pitch preserved | positives only | measured durations 220–720 ms; ±10 % stays in range |
| SpecAugment | ≤2 freq / ≤2 time masks | train only, feature domain | microWakeWord + Speech Commands practice |

**Everything seeded.** A fixed master seed plus a per-sample derived seed, both recorded in the
manifest, so any clip is reproducible from metadata alone.

## 9. Evaluation design — the part that makes it honest

With one real speaker, the evaluation is where this project can most easily fool itself.
Three rules, all inherited from D-005 and none negotiable:

1. **The test split is real human INMP441 audio only.** No TTS, no augmentation, ever.
2. **Speaker-disjoint is impossible, so it is not claimed.** The substitute control is
   **session-disjoint**: test uses recordings from a *different session* than training
   (`DEMO_DATASET_SPEC.md` EV-2). This catches session overfitting, which cost a predecessor a
   **~12×** optimistic false rate. It does **not** substitute for speaker independence.
3. **Headline numbers come from continuous audio**, not clips — FRR at a fixed FA/h, with the
   observation duration and Poisson CI stated.

## 10. What this research concluded, in one table

| Question | Answer |
|---|---|
| Can we build a defensible dataset with one speaker? | **Yes, for a demo** — with ~1,090 TTS voices for training and real audio reserved for evaluation |
| Should TTS be the positive source? | **Yes for training**, never for test |
| Which voices matter most? | **L2-ARCTIC** (non-native English) and **Indic** (native क्ष) |
| Are pre-computed negative features reusable? | **No** — wrong frontend geometry |
| Are random English words useful negatives? | **No** — FakeWake shows FA concentrates on shared snippets |
| Biggest free asset already present? | **Speech Commands on disk**, CC BY 4.0 |
| What must remain real? | **Test split, room tone, background, and the device channel** |
| What may we claim? | Detection and FA/h **for this speaker, this room** — **never speaker independence** |

## Sources

- [Speech Commands: A Dataset for Limited-Vocabulary Speech Recognition (arXiv 1804.03209)](https://arxiv.org/pdf/1804.03209)
- [microWakeWord](https://github.com/kahrendt/microWakeWord) · [micro-wake-word (OHF-Voice)](https://github.com/OHF-Voice/micro-wake-word)
- [piper-sample-generator](https://github.com/rhasspy/piper-sample-generator)
- [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)
- [FakeWake: Understanding and Mitigating Fake Wake-up Words (arXiv 2109.09958)](https://arxiv.org/html/2109.09958)
- [Streaming keyword spotting on mobile devices (arXiv 2005.06720)](https://arxiv.org/abs/2005.06720)
- [OpenSLR-28 — Room Impulse Response and Noise Database](https://www.openslr.org/28/)
- [MUSAN (arXiv 1510.08484)](https://arxiv.org/pdf/1510.08484)
