# DATASET_SPEC.md — production KWS dataset for `Takshila`

**Date:** 2026-09-09 · **Status:** design complete, **collection not started**
**Target:** ESP32-S3-WROOM-1-N16R8 + INMP441, continuous always-listening KWS
**Keyword:** `Takshila` — confirmed and binding, `DECISIONS.md` **D-011**

This is the build specification. It is the input to collection, not a document to redesign.
Research behind the keyword and the first-cut data requirements: `KEYWORD_SELECTION.md`.

> **Keyword suitability re-check (required before designing):** no evidence encountered during
> this design indicates `Takshila` is unsuitable. Its 7 phonemes, 4 manner classes and
> 5 places of articulation survive every constraint applied here, and its confusable
> neighbourhood is enumerable and collectable (§9). **No redesign is proposed.** The one
> unresolved risk is unchanged and is *measurement*, not selection: no false-alarm rate has
> been measured, and §37 exists to measure it.

---

# PART I — KEYWORD AND CLASS DEFINITIONS

## 1. Target keyword

**`Takshila`** — "tuk-SHEE-laa". One word. 3 syllables. No carrier phrase.

The one-word decision is architectural, not stylistic: a carrier ("Hey Takshila") runs
~1.0–1.2 s and does not fit the 1.0 s model context, and enlarging that input cost a measured
**26.6×** in inference time on this hardware `[prior-build]`.

## 2. Phonetic representation

| Layer | Representation |
|---|---|
| IPA (Indian English) | **/t̪əkˈʃiː.laː/** |
| Syllables | `t̪ək` · `ʃiː` · `laː` (CVC · CV · CV) — stress on σ2 |
| Phoneme sequence | /t̪/ /ə/ /k/ /ʃ/ /iː/ /l/ /aː/ — **7 phonemes** |
| ARPAbet-ish | `T AH0 K SH IY1 L AA0` |
| Devanagari | तक्षशिला / तक्षिला |
| Manner classes | stop, stop, fricative, lateral, vowel — **4 distinct** |
| Places | dental, velar, postalveolar, alveolar, + vowel space — **5 distinct** |
| Expected duration | **520–780 ms** normal rate; 380–520 ms fast; 700–1000 ms slow |
| Spectral signature | /ʃ/ gives sustained **3–8 kHz** energy — the INMP441's cleanest band, above the sub-100 Hz region carrying 64.6 % of its noise energy `[prior-build]` |

**Acoustic landmarks** the detector can key on, in order: /t̪/ burst → short schwa → /k/ burst →
**/ʃ/ frication plateau (the longest steady-state segment)** → /iː/ with high F2 → /l/ transition
→ /aː/ with low F2. The /k/→/ʃ/ transition is the single most distinctive event.

## 3. Expected pronunciation variants

All of these are **positives** unless marked otherwise. They must be prompted for, recorded, and
labelled — not discovered later.

| # | Variant | Realisation | Expected share | Class |
|---|---|---|---|---|
| V1 | Canonical | /t̪əkˈʃiː.laː/ | ~60 % | positive |
| V2 | Full first vowel | /t̪ʌkˈʃiː.laː/ ("tuck-shee-laa") | ~15 % | positive |
| V3 | Schwa-dropped, fast | /kˈʃiː.laː/ ("kshee-laa") | ~10 % | positive |
| V4 | Hyper-articulated | /t̪ək.ʃi.laː/ (even stress, 3 clear beats) | ~8 % | positive |
| V5 | Final-vowel shortened | /t̪əkˈʃiː.lə/ | ~5 % | positive |
| V6 | Aspirated onset | /t̪ʰəkˈʃiː.laː/ | ~2 % | positive |
| V7 | **"Taxila"** (English 2–3 syll) | /ˈtæk.sɪ.lə/ | prompt explicitly | **positive (flagged)** |
| V8 | Epenthetic | /t̪ə.kə.ˈʃiː.laː/ ("tuk-uh-shee-laa") | non-Indian speakers | **positive (flagged)** |
| V9 | **"Takshashila"** (4 syll, full form) | /t̪ək.ʃəˈʃiː.laː/ | prompt explicitly | **near_homophone, NOT positive** |

**V7 and V8 are recorded but flagged** (`variant_accept=conditional`). They enter training only
if an A/B on the Phase-C harness shows they do not raise FA. **V9 is a negative** — it is a
different word and admitting it would widen the decision boundary for no gain.

## 4. Positive class definition

A clip is `positive` **iff all four hold**:

1. The **complete** keyword — all 7 phonemes, /t̪/ burst through the /aː/ release — is inside the
   1.000 s window.
2. **≥ 60 ms of margin** exists between each keyword edge and the window edge, so the detector
   never sees a truncated onset or offset labelled as complete.
3. The realisation is one of **V1–V8** (V9 excluded).
4. It passes every QC rule in §29.

**Anything else containing keyword audio is a negative.** Specifically, a window holding
**≥ 25 % but < 100 %** of the keyword is `hard_negative/partial` (§5) — never positive, never
discarded. This single rule is the most important in the document: the predecessor's deployed
model fired on **49.7 %** of realistic sliding windows while its curated clip set reported
**10.7 %** — a **4.6× optimism** caused precisely by training without partial-keyword negatives
`[prior-build]`.

**Keyword position within the window is sampled, not centred.** For every raw utterance, the
1.0 s window is cut at multiple offsets so the keyword onset is uniformly distributed across the
admissible range. **Offset sampling is not augmentation** — it is the correct sampling of the
distribution the device actually sees, and it therefore applies to **train, validation and test
alike** (§25).

## 5. Unknown / hard-negative class definition

`hard_negative` — speech that shares decisive phonetic material with the keyword. Derived per
FakeWake's finding that false accepts concentrate on **shared phonetic snippets**, and that
**Levenshtein distance fails** to predict them.

| Sub-label | Definition | Target unique items |
|---|---|---|
| `hard_negative/ksha` | Words containing the क्ष conjunct — the /kʃ/ decisive middle | 20 |
| `hard_negative/taks` | Words with a /tæks/ or /t̪əks/ onset | 18 |
| `hard_negative/shiil` | Words with a stressed /ʃiːl/ nucleus | 12 |
| `hard_negative/neighbour` | Full-word near-neighbours of the keyword | 12 |
| `hard_negative/boundary` | Cross-word sequences that reconstruct the keyword | 12 |
| **`hard_negative/partial`** | **Windows holding 25–99 % of a real keyword utterance** | derived, not spoken |

**The hardest items go in `train`.** The predecessor shipped 10 confusable phrases with its
three hardest present only in validation/test — a self-inflicted failure this spec forbids
(§27).

## 6. Silence class

`silence` — no intentional acoustic event.

| Sub-label | Source | Target clips |
|---|---|---|
| `silence/digital` | true zero + dither at −90 dBFS | 200 |
| `silence/roomtone_quiet` | INMP441 in a quiet room, no occupant activity | 800 |
| `silence/roomtone_hvac` | fan / AC running, no speech | 800 |
| `silence/mic_floor` | INMP441 self-noise, anechoic-ish (61 dBA SNR part) | 200 |

Real room tone dominates deliberately: the device idles in rooms, not in digital silence, and
the INMP441's own noise floor is a real signal the model must learn to ignore.

## 7. Background-noise class

`background` — non-speech acoustic events.

| Sub-label | Content | Source | Target |
|---|---|---|---|
| `background/hvac` | fan, AC, air handler | **own recording** | 800 |
| `background/impact` | door, keyboard, footsteps, chair, cutlery | **own recording** | 900 |
| `background/electronic` | phone notifications, laptop chimes, chargers | **own recording** | 400 |
| `background/outdoor` | traffic, horns, wind, rain, birds | own + MUSAN | 900 |
| `background/music` | instrumental and vocal music | **MUSAN music** | 1,000 |
| `background/crowd` | non-intelligible babble, canteen, corridor | own + MUSAN | 1,000 |

**Music and babble are mandatory, not optional.** They are the two background types most likely
to contain accidental phone sequences, and an energy-only VAD does not separate them from speech.

## 8. Speech-negative class

`speech_negative` — genuine speech with **no phonetic relationship** to the keyword. This is the
bulk-volume class and the main defence against everyday false activation.

| Sub-label | Source | Licence | Target |
|---|---|---|---|
| `speech_negative/read_en` | LibriSpeech | CC BY 4.0 | 4,000 |
| `speech_negative/accented_en` | **Common Voice, Indian English filtered** | CC0 | 4,000 |
| `speech_negative/commands` | Google Speech Commands | CC BY 4.0 | 2,000 |
| `speech_negative/conversational` | MUSAN speech | CC/PD, commercial-safe | 1,500 |
| `speech_negative/own_freespeech` | **our own speakers, 60 s each** | own | 1,500 |
| `speech_negative/indic_l1` | Hindi/Tamil/Telugu/Bengali/Marathi speech | Common Voice (CC0) | 2,000 |

`speech_negative/indic_l1` matters specifically for this keyword: the क्ष conjunct is frequent in
Indian-language speech, so Indic negatives carry natural hard negatives we cannot script.

## 9. Near-homophone class

`near_homophone` — the tightest confusables, held as a **first-class class** so FA against them
is reported separately rather than hidden inside a general negative rate.

### Tier 1 — क्ष family (highest priority; frequent in real Indian speech)

`shiksha` · `raksha` · `lakshya` · `moksha` · `daksha` · `paksha` · `rakshak` · `suraksha` ·
`pariksha` · `aksha` · `vriksha` · `diksha` · `kaksha` · `bhiksha` · `samiksha` · `apeksha` ·
`upeksha` · `lakshmi` · `akshay` · `takshak`

### Tier 2 — /tæks/ onset family

`taxi` · `tax` · `taxes` · `taxable` · `tax law` · `tax filing` · `taxonomy` · `tactical` ·
`taxidermy` · `tax-free` · `taximeter` · `taxpayer` · `tax return` · `taxing` · `tactics` ·
`tax slab` · `taxied` · `taxonomic`

### Tier 3 — stressed /ʃiːl/ nucleus

`Sheila` · `she'll` · `shield` · `shielding` · `shilling` · `Shilpa` · `sheeling` · `she looks` ·
`Shimla` · `she left` · `shear law` · `Sheela's`

### Tier 4 — full-word near-neighbours

**`Takshashila`** (V9) · `Taxila` (as a *place* reference, not the keyword) · `Takshak` ·
`Takshaka` · `Thakshila` · `Dakshila` · `Lakshila` · `Takshira` · `Takshina` · `Takshan` ·
`Takshit` · `Taksheel`

### Tier 5 — cross-word boundary reconstructions

"talk she'll ah" · "tak… Sheela" · "attack shield" · "that's a shield" · "take a seat, Sheila" ·
"tax she left" · "stock she'll allow" · "look, Sheila" · "black shield" · "back-shift law" ·
"the tax he laid" · "shock, she'll adapt"

**74 unique items.** Each must be spoken by **≥ 10 distinct voices** (human + TTS), and Tiers 1–2
must appear in **train**.

---

# PART II — ACOUSTIC CONDITIONS

## 10. Environmental conditions

| ID | Environment | RT60 (approx) | Sessions |
|---|---|---|---|
| E1 | Small quiet room (bedroom/office) | 0.3–0.5 s | 40 % |
| E2 | Classroom / lab, occupied | 0.5–0.8 s | 25 % |
| E3 | Corridor / stairwell (hard surfaces) | 0.8–1.5 s | 10 % |
| E4 | Large hall / canteen | > 1.0 s + babble | 10 % |
| E5 | Outdoor / semi-outdoor | ~0 s, traffic | 10 % |
| E6 | Room with running fan or AC | 0.3–0.5 s + broadband | 5 % |

**Every speaker records in ≥ 2 environments.** Environment is logged, never inferred.

## 11. Speaker diversity requirements

| Attribute | Target | Minimum |
|---|---|---|
| **Total speakers** | **30** | **15** |
| Gender balance | ≥ 40 % each of male/female | ≥ 30 % |
| Age bands | 18–25 (60 %), 26–40 (25 %), 41+ (15 %) | ≥ 2 bands |
| Distinct L1 backgrounds | **≥ 6** | ≥ 4 |
| Speakers reserved for **test** | **5, untouched** | 3 |
| Speakers reserved for validation | 5 | 3 |

**Speaker count is the binding constraint of this project.** Espressif's production bar is
**> 500 speakers with ≥ 100 children**; we target 30. That gap is why keyword choice was
optimised so hard (`KEYWORD_SELECTION.md`) and why §33's minimum is stated honestly.

**Children are out of scope.** Recording minors introduces consent and ethics requirements this
project cannot properly discharge. The consequence — degraded performance on child voices — is
declared, not hidden.

## 12. Accent diversity requirements

L1 backgrounds to target, ≥ 6 distinct: **Hindi · Tamil · Malayalam · Telugu · Bengali ·
Marathi · Kannada · Gujarati · Punjabi**.

Accent-driven realisations to capture explicitly, from `KEYWORD_SELECTION.md` §1.4:

| Feature | Expected effect on `Takshila` |
|---|---|
| Retroflex vs dental /t̪/ | onset burst spectrum shifts — **both are positive** |
| Vowel merger | /ə/ may raise toward /ʌ/ or /a/ — **V2** |
| क्ष realisation | /kʃ/ vs /kʂ/ vs /tʃʰ/ regional variants — **all positive** |
| South Indian euphonic onset | slight /j/ or /w/ glide before initial vowel-like schwa |
| Syllable-timed rhythm | more even stress across the three syllables — **V4** |

**No accent may be corrected during recording.** The prompt is the written word; whatever the
speaker naturally produces is the ground truth.

## 13. Distance variation

| ID | Distance | Share of positives | Rationale |
|---|---|---|---|
| D1 | **0.3 m** | 25 % | near-field, held device |
| D2 | **1.0 m** | 35 % | primary use, Espressif's own reference |
| D3 | **2.0 m** | 25 % | across a desk / small room |
| D4 | **3.0 m** | 15 % | far-field, Espressif's second reference |

This extends Espressif's 1 m / 3 m protocol with a near-field and a mid point. Level drops
~6 dB per doubling of distance, so D4 clips will sit near the noise floor — that is the point.

## 14. Microphone orientation variation

| ID | Orientation | Share |
|---|---|---|
| O1 | On-axis (0°, speaker facing mic) | 55 % |
| O2 | 45° off-axis | 20 % |
| O3 | 90° off-axis (side) | 15 % |
| O4 | 180° (speaker turned away) | 10 % |

The INMP441 is an omnidirectional MEMS part, so orientation mostly changes **HF roll-off and the
direct-to-reverberant ratio** — exactly the /ʃ/ band the detector relies on. O4 is the hardest
condition and is deliberately included.

## 15. Speaking volume variation

| ID | Volume | Share | Note |
|---|---|---|---|
| L1 | **Whisper** (unvoiced) | 10 % | hardest case: /ʃ/ survives, vowels do not |
| L2 | Soft | 20 % | |
| L3 | Normal | 50 % | |
| L4 | Loud / raised | 20 % | risks clipping — QC checks it |

Whisper is included because it is the realistic late-night / shared-office case, and because it
tests whether the model has learned the /ʃ/ landmark or merely loudness.

## 16. Speaking rate variation

| ID | Rate | Keyword duration | Share |
|---|---|---|---|
| R1 | Slow / deliberate | 700–1000 ms | 25 % |
| R2 | Normal | 520–780 ms | 50 % |
| R3 | Fast / casual | 380–520 ms | 25 % |

Matches Espressif's 5-fast / 5-normal / 5-slow protocol. **R3 produces variant V3** (schwa
dropped), which must be labelled as such so its detection rate can be reported separately —
it is the most likely systematic failure.

## 17. Reverberation conditions

Two sources, kept distinct:

| Source | Use | Applies to |
|---|---|---|
| **Real** — environments E1–E6 recorded as-is | ground truth | all splits |
| **Simulated** — convolution with OpenSLR-28 RIRs (Apache 2.0), RT60 0.2–1.5 s | augmentation | **train only** |

**Simulated reverb never enters validation or test.** Test reverb is real reverb, from real
rooms, from held-out speakers. Otherwise the test measures our RIR set, not the world.

## 18. Noise conditions

| Condition | SNR | Share of positives | How |
|---|---|---|---|
| Clean | > 30 dB | 30 % | real quiet room |
| Light | 20–30 dB | 25 % | real |
| Moderate | 10–20 dB | 25 % | real + mixed |
| Heavy | 0–10 dB | 15 % | real + mixed |
| Extreme | −5–0 dB | 5 % | mixed only |

Same discipline as reverb: **test-set noise is recorded, not mixed.** Mixed-noise clips are
train-only, plus a clearly-labelled `val_robustness` subset used for reporting, never for model
selection.

## 19. Recording-device conditions

| ID | Device | Role | Share |
|---|---|---|---|
| **H1** | **INMP441 + ESP32-S3, the deployment hardware** | **primary — ground truth** | ≥ 70 % |
| H2 | Reference USB condenser mic, 16 kHz | insurance + channel modelling | parallel capture |
| H3 | Laptop built-in mic | device-mismatch robustness | 15 % |
| H4 | Phone mic | device-mismatch robustness | 15 % |

> ### ⚠ Dependency: H1 requires the pin map (blocker B-1)
> Device-matched recording is the single biggest advantage available to this project —
> Espressif must generalise from hi-fi microphones to cheap MEMS parts; **we can record on the
> deployment part itself.** But the INMP441 is not wired until the authoritative pin map arrives.
>
> **Mitigation: dual capture.** Every session records H1 and H2 **simultaneously**, time-aligned.
> If H1 is unavailable when a session runs, H2 preserves the session and the H1-matched version
> can be approximated later by convolving with a measured INMP441 channel response. That
> approximation is **inferior to a real recording and must be labelled `device_simulated=true`**.
>
> **Recommendation: resolve B-1 before collection starts.** Re-recording 30 speakers is not
> feasible; recording them once, correctly, is.

---

# PART III — TECHNICAL FORMAT

## 20. Sampling rate

**16,000 Hz.** No resampling anywhere in the pipeline. Matches the model input, the ESP-SR
specification, and the INMP441's I²S configuration (64 SCK/frame ⇒ SCK = 1.024 MHz).

The measured device rate was **16,001.60 Hz (+0.010 %)** `[prior-build]` — re-measure in task A5;
if it holds, the deviation is negligible and no correction is applied.

## 21. Bit depth

**16-bit signed PCM, little-endian.** The INMP441 emits 24-bit left-justified in a 32-bit slot;
firmware keeps the **upper 16 bits**. Getting that shift wrong is a silent 48 dB level error, so
the capture tool asserts it (§29 QC-8).

Raw sessions may be archived at 24-bit if the tool supports it; **the dataset is 16-bit.**

## 22. Channel configuration

**Mono, single channel.** INMP441 `L/R` tied to GND ⇒ **LEFT** channel only. The right slot is
discarded in firmware. Stereo reference recordings (H2) are downmixed to mono at build time.

## 23. Target clip duration

**Exactly 1.000 s = 16,000 samples.**

Derived from the model input, not chosen freely: 49 frames × 20 ms hop + 25 ms window = **985 ms**,
padded to a round 1.000 s. Every clip in every class is exactly 16,000 samples; the builder
rejects anything else (QC-1).

Raw session files are **unbounded length** and are never trimmed — clips are *cut from* them.

## 24. Preprocessing pipeline

Identical on host and device. **A host/device parity test must pass before any on-device
accuracy claim** (`ARCHITECTURE.md` §3; the bar is the prior build's max abs diff 0.000112 /
correlation 1.0000000000).

```
INMP441 I2S 24-in-32  →  keep upper 16 bits  →  int16 PCM @ 16 kHz mono
  → frame 400 samples (25 ms), hop 320 samples (20 ms)
  → periodic Hann window
  → 512-point FFT  →  power spectrum
  → 40 mel filters, 125–7500 Hz
  → log
  → orthonormal DCT-II  →  keep 13 MFCC
  → per-coefficient (mean, std) normalisation  ← statistics from TRAIN ONLY
  → 49 × 13 tensor
```

**Deliberately NOT done, each for a reason:**

| Not applied | Why |
|---|---|
| Per-clip loudness normalisation | destroys the level information distance/volume robustness depends on; level diversity comes from real recordings and gain augmentation instead |
| Pre-emphasis | the 125 Hz mel floor already discards the sub-100 Hz region holding 64.6 % of mic noise `[prior-build]` |
| Noise suppression / AGC | would differ between host and device and break parity |
| Resampling | source and target are both 16 kHz |
| Silence trimming | the model must handle leading/trailing silence — that is the streaming condition |

**Normalisation statistics are computed on `train` only** and emitted into a generated header.
A single global mean/std collapsed c2..c12 and caused training to degenerate to the majority
class `[prior-build]` — hence per-coefficient.

## 25. Augmentation strategy

### 25.1 The distinction that governs everything here

| | Definition | Applies to |
|---|---|---|
| **Offset sampling** | cutting the 1.0 s window at many positions over a real utterance | **train, val, test** — it is the real inference distribution, not augmentation |
| **Augmentation** | synthesising new conditions not present in the recording | **train only** (+ a labelled `val_robustness` subset) |

Conflating these is how a clip-trained model looks good and fails on hardware. Offsets are
*sampling*; noise mixing is *augmentation*.

### 25.2 Offset sampling — mandatory, all splits

For each raw positive utterance of duration *d*, cut **6 windows** with keyword onset uniformly
distributed such that the ≥ 60 ms margin rule (§4) holds. From the same utterance also cut
**2 partial windows** at 25–75 % coverage, labelled `hard_negative/partial`.

Every clip records `keyword_onset_ms` and `keyword_offset_ms` so positional robustness can be
reported and so the model's positional bias is measurable.

### 25.3 Augmentation — train only

| Technique | Parameters | Applied to |
|---|---|---|
| Additive noise | SNR −5…30 dB, from `background` **train partition only** | positive, near_homophone, hard_negative |
| RIR convolution | OpenSLR-28, RT60 0.2–1.5 s | positive, near_homophone |
| Gain | −12…+6 dB, no clipping | all |
| Time stretch | 0.9×–1.1×, **pitch preserved** | positive only |
| Pitch shift | ±1 semitone **maximum** | positive only |
| SpecAugment | ≤ 2 freq masks (≤ 4 bins), ≤ 2 time masks (≤ 6 frames) | feature domain, train only |
| Band-limit | simulate INMP441 response on non-H1 audio | H3/H4/public audio |

**Hard rules:**

1. **The test split is never augmented.** Not once, not for reporting.
2. **An augmented clip inherits its source's split.** Enforced by construction (§28).
3. **Noise mixed into a training clip comes only from the training noise partition.** Noise
   recordings are split too — otherwise the test noise has been seen.
4. **Time stretch ≤ ±10 %.** Beyond that the keyword duration leaves the observed range and the
   model learns a distribution that does not occur.
5. **Augmentation multiplies clips, not information.** The predecessor inflated 110 utterances
   ×7.2 and still failed. Augmentation targets are capped at **×4 on positives** and the raw
   speaker count remains the figure of record.

---

# PART IV — SPLITS, INTEGRITY, METADATA

## 26. Train / validation / test strategy

| Split | Speakers | Purpose | May be used to tune? |
|---|---|---|---|
| `train` | **20** (67 %) | fit model weights | yes |
| `validation` | **5** (17 %) | early stopping, architecture choice, **threshold sweep** | yes |
| `test` | **5** (17 %) | **final evaluation, once** | **NO** |

Plus three continuous-audio sets (§37), assigned as: **SWEEP** (from validation speakers +
validation noise) and **VALIDATE** (from test speakers + unseen noise). The operating point is
chosen on SWEEP and reported on VALIDATE.

**The final threshold is chosen on `validation` / SWEEP and never on `test` / VALIDATE.**

## 27. Speaker-disjoint split policy

**No speaker appears in more than one split. No exceptions, and none are justified here.**

The predecessor could not make a speaker-independence claim because its entire positive class
was one speaker. A speaker-disjoint test split is the only thing that makes
"speaker-independent" a measurable claim rather than a marketing sentence.

Assignment procedure:

1. Split by `speaker_id` **before any clip is cut**, with a fixed seed, recorded in the manifest.
2. Stratify so each split spans ≥ 3 L1 backgrounds and both genders.
3. Test speakers are chosen **first** and quarantined.
4. Public-corpus speakers (LibriSpeech, Common Voice) are also split by their own speaker IDs —
   the same policy applies to negatives.
5. **Hard negatives and near-homophones are split by voice too.** A TTS voice used in train may
   not appear in test.

## 28. Leakage prevention

| # | Leak vector | Control |
|---|---|---|
| L-1 | Same speaker across splits | split by `speaker_id` first; builder asserts empty intersection |
| L-2 | **Augmented copy of a training clip in test** | every clip carries `source_utterance_id`; augmented clips inherit split; builder asserts no `source_utterance_id` spans splits |
| L-3 | Two windows of the same utterance in different splits | offsets inherit the utterance's split |
| L-4 | Same session across splits | `session_id` is also asserted disjoint |
| L-5 | **Test noise used in training** | noise/RIR pools are split; train mixes only train noise |
| L-6 | Same TTS voice across splits | `voice_id` asserted disjoint |
| L-7 | Public-corpus speaker across splits | corpus speaker ID asserted disjoint |
| L-8 | Threshold tuned on test | test manifest is hash-locked; the eval script refuses to run in sweep mode against it |
| L-9 | Repeated evaluation on test | every access to test is logged with a timestamp and a reason |
| L-10 | Same recording appearing in both a clip set and a continuous stream | stream sources are drawn from a reserved partition |

The builder runs every assertion and **fails the build** on any violation. Leakage is not a
warning.

## 29. Quality-control rules

Applied at capture time where possible (fail fast, re-record) and again at build time.

| # | Rule | Threshold | Action |
|---|---|---|---|
| QC-1 | Clip length | exactly 16,000 samples | reject |
| QC-2 | Format | 16 kHz / 16-bit / mono | reject |
| QC-3 | Clipping | < 0.1 % samples at full scale | reject; flag if any |
| QC-4 | Level | −40 dBFS ≤ RMS ≤ −6 dBFS | reject, re-record |
| QC-5 | SNR | ≥ −5 dB estimated | reject |
| QC-6 | DC offset | \|mean\| < 0.002 FS | reject |
| QC-7 | Dropouts | no gap > 20 ms of exact zeros mid-utterance | reject — indicates I²S/DMA loss |
| QC-8 | **Bit alignment** | plausible dynamic range; not compressed into ±2^8 | reject — the 48 dB shift error |
| QC-9 | Keyword completeness | annotated onset/offset within margin (§4) | reclassify as `partial`, not reject |
| QC-10 | Mispronunciation | matches V1–V8; V9 excluded | reclassify as `near_homophone` |
| QC-11 | Truncated take | speaker cut off | reject, re-record |
| QC-12 | Cross-talk | second speaker audible | reject from positives; usable as `background/crowd` |
| QC-13 | Duplicate | identical SHA-256 | reject |
| QC-14 | Duration sanity | keyword 300–1200 ms | flag for review |
| QC-15 | Metadata completeness | all required fields present | reject |

**Rejected takes are archived, not deleted** (`data/recordings/<speaker>/rejected/`) with the
reason — the predecessor's "23 rejected (auditable)" practice was good and is retained.

**Target reject rate ≤ 10 %.** Higher means the protocol or the room needs fixing, not the data.

## 30. Metadata schema

Per-clip row in the manifest CSV; one `session.json` per recording session.

```jsonc
// data/recordings/<speaker_id>/<session_id>/session.json
{
  "schema_version": "1.0",
  "session_id": "S007_2026-10-02_E1",
  "speaker": {
    "speaker_id": "SPK007",            // pseudonymous, never a real name
    "gender": "female",                 // male | female | other | undisclosed
    "age_band": "18-25",
    "l1": "tamil",
    "english_proficiency": "fluent",
    "consent": { "given": true, "form_version": "1.0", "date": "2026-10-02",
                 "scope": "research_and_demo", "withdrawable": true }
  },
  "environment": { "id": "E1", "description": "small office, door closed",
                   "approx_rt60_s": 0.4, "measured_noise_floor_dbfs": -62 },
  "devices": [
    { "id": "H1", "type": "inmp441_esp32s3", "role": "primary",
      "firmware_git_sha": "…", "sample_rate_hz": 16000, "bit_depth": 16,
      "i2s_shift_verified": true },
    { "id": "H2", "type": "usb_condenser", "role": "reference" }
  ],
  "conditions": { "distances_m": [0.3,1.0,2.0,3.0], "orientations_deg": [0,45,90,180],
                  "volumes": ["whisper","soft","normal","loud"],
                  "rates": ["slow","normal","fast"] },
  "operator": "OP1",
  "notes": "AC running in block D"
}
```

Manifest columns (one row per **clip**):

| Column | Example | Purpose |
|---|---|---|
| `clip_id` | `SPK007_S007_u012_o3` | unique |
| `filepath` | `train/positive/SPK007_...wav` | relative to variant root |
| `class` | `positive` | 6-way label |
| `sub_label` | `hard_negative/ksha` | fine-grained |
| `model_target` | `keyword` | 3-way training target (§ below) |
| `speaker_id` | `SPK007` | **split key** |
| `session_id` / `utterance_id` / `source_utterance_id` | | **leakage keys** |
| `variant` | `V3` | pronunciation variant |
| `keyword_onset_ms` / `keyword_offset_ms` | `210` / `790` | positional analysis |
| `keyword_coverage` | `1.00` | 1.0 = complete; 0.25–0.99 = partial |
| `distance_m` / `orientation_deg` / `volume` / `rate` | | robustness breakdowns |
| `environment_id` / `approx_rt60_s` / `snr_db` | | robustness breakdowns |
| `device_id` / `device_simulated` | `H1` / `false` | device-match analysis |
| `augmentation` | `none` \| `noise_snr10` \| `rir_0p8` | train-only marker |
| `augment_chain` | `["gain_-3","noise_snr12"]` | reproducibility |
| `split` | `train` | |
| `source_corpus` / `source_license` / `source_url` | | provenance |
| `sha256` / `duration_samples` / `rms_dbfs` / `peak_dbfs` / `clipped_samples` | | QC + integrity |
| `qc_status` / `qc_flags` | `pass` / `[]` | |
| `build_version` / `created_utc` | | reproducibility |

**Label granularity ≠ model output granularity.** The 6-way `class` supports analysis and error
mining; `model_target` maps it to the 3 classes the network actually predicts:

| `class` | `model_target` |
|---|---|
| `positive` | `keyword` |
| `near_homophone`, `hard_negative`, `speech_negative` | `unknown` |
| `background`, `silence` | `background` |

Keeping both means the FA rate **against near-homophones specifically** is reportable without
retraining — which is the number that will decide whether the keyword survives contact with
reality.

## 31. Licensing / provenance schema

Every clip carries `source_corpus`, `source_license`, `source_url`, `attribution_required`,
`commercial_use_permitted`. A `LICENSES.md` is generated at build time listing every corpus used
and its attribution text.

| Source | Licence | Commercial | Attribution | Verdict |
|---|---|---|---|---|
| **Own recordings** | project-owned, consented | yes | — | ✅ primary |
| LibriSpeech | CC BY 4.0 | ✅ | required | ✅ |
| Google Speech Commands | CC BY 4.0 | ✅ | required | ✅ |
| MUSAN | CC / US public domain, curated commercial-safe | ✅ | per-file | ✅ |
| OpenSLR-28 RIRs | Apache 2.0 | ✅ | notice | ✅ |
| **Mozilla Common Voice** | **CC0** | ✅ | none required | ✅ **preferred** |
| **ESC-50** | **CC BY-NC 3.0** | ❌ **non-commercial** | required | ⚠ **avoid** — record our own instead |
| Piper TTS (`OHF-Voice/piper1-gpl`) | **GPL-3.0** engine | engine copyleft | per-voice | ⚠ output is not a derivative of the synthesiser, **but log each voice model's own licence** |

**Two standing rules.** (1) **Prefer Common Voice (CC0) and our own recordings over ESC-50** —
its NC clause is the only genuine restriction in the set and the predecessor depended on it.
(2) If TTS is used, `voice_id` and that voice's licence are recorded per clip, not just the
engine's.

**Consent.** Every human speaker signs a written form covering research use, demonstration at
SIH, retention, and withdrawal. Speaker IDs are pseudonymous. **No real names, no contact
details, no audio of minors.** Consent status is a manifest field and clips without it fail QC-15.

---

# PART V — SIZE AND EVALUATION SETS

## 32. Target dataset size

| Class | Raw human utterances | Clips after offset sampling + train augmentation |
|---|---|---:|
| `positive` | **1,440** (30 spk × 48) | **8,640** |
| `hard_negative/partial` | derived | 2,880 |
| `near_homophone` | 600 human + 2,200 TTS | 3,400 |
| `hard_negative` (non-partial) | 600 human + 1,800 TTS | 2,900 |
| `speech_negative` | 1,500 own + public | 15,000 |
| `background` | ~2,500 own + MUSAN | 5,000 |
| `silence` | ~2,000 own | 2,000 |
| **Total clips** | | **≈ 39,800** |

Continuous audio: **SWEEP 2 h · VALIDATE 20 h · detection stream 60 min** (§37).

Approximate storage: 39,800 × 32 kB ≈ **1.3 GB** of clips, plus **~8 GB** of raw sessions and
**~2.5 GB** of continuous audio. Budget **~15 GB**.

## 33. Minimum acceptable dataset size

Below this the project cannot make a defensible claim.

| Class | Absolute minimum | Consequence of being at the floor |
|---|---|---|
| **Speakers** | **15** (9 train / 3 val / **3 test**) | speaker-independence claim becomes weak; must be stated |
| `positive` raw utterances | **600** (15 × 40) | |
| **Test positives (raw, held-out speakers)** | **≥ 120** | at 120 trials, 95 % CI half-width ≈ **±5.4 pp** at p≈0.9 |
| `near_homophone` unique items | 40 (of the 74 designed) | Tiers 1–2 are mandatory |
| `speech_negative` clips | 5,000 | |
| `background` + `silence` | 2,000 | |
| **Continuous FA audio** | **10 h** | see §37 for what 10 h can and cannot resolve |

**Statistical note, stated honestly.** The deprecated corpus had **17** test positives, giving
roughly **±20 pp** — it could not settle anything. The 120-minimum gives ±5.4 pp and the 240
target gives **±3.8 pp**. That improvement is the main *measurable* benefit of this redesign.

## 34. Evaluation-only recordings

Collected **specifically for evaluation** and never used for training, tuning or threshold
selection.

| Set | Content | Size |
|---|---|---|
| **EV-1 Held-out speakers** | 5 speakers, full session protocol | 240 positives + 100 negatives |
| **EV-2 Fresh-day re-record** | 3 *training* speakers re-recorded ≥ 2 weeks later, different room | 150 positives |
| **EV-3 Adversarial confusables** | the full 74-item near-homophone list, voices unseen in train | 740 clips |
| **EV-4 In-the-wild** | unscripted use in a real room, keyword spoken naturally amid conversation | 60 min |
| **EV-5 Demo rehearsal** | the actual demo script, actual room, actual distances | 30 min |

**EV-2 exists because of a specific predecessor failure**: held-out windows came from the same
narrow recording sessions as training, leaving the false rate optimistic by roughly **12×**
`[prior-build]`. Same-speaker-different-day is the control that catches session overfitting, and
it is the **only** justified same-speaker crossing in this spec — it is an *evaluation* set that
never touches training.

## 35. Real-hardware recordings

**≥ 70 % of all positives must be recorded through the INMP441 on the ESP32-S3 (H1).**

| Requirement | Detail |
|---|---|
| Capture path | INMP441 → I²S 24-in-32 → upper 16 bits → 16 kHz mono PCM |
| Firmware | a dedicated recorder sketch; its git SHA is logged per session |
| Verification | `i2s_shift_verified` asserted per session; QC-8 enforces it |
| Streaming | over USB serial or Wi-Fi to the host recorder tool |
| Parallel | H2 reference mic records simultaneously, time-aligned |
| **All of EV-1, EV-4, EV-5** | **must be H1** — final numbers must come from the deployment device |

**This is gated on blocker B-1 (pin map).** See the boxed warning in §19. The order of
operations is: pin map → wire → A4/A5 bring-up → recorder firmware → pilot session → collection.

## 36. Hard-negative test set

A standalone, never-trained-on set for reporting FA against confusables specifically.

| Partition | Content | Size |
|---|---|---|
| HN-T1 | क्ष family, **voices unseen in train** | 200 clips |
| HN-T2 | /tæks/ family, unseen voices | 180 |
| HN-T3 | /ʃiːl/ family, unseen voices | 120 |
| HN-T4 | full-word neighbours incl. **`Takshashila` (V9)** and `Taxila`-as-place | 120 |
| HN-T5 | cross-word boundary reconstructions | 120 |
| **HN-T6** | **partial-keyword windows from held-out speakers** | **240** |

Reported as **FA rate per tier**, not as one number. If HN-T1 (क्ष) shows a high rate, that is
the keyword decision failing and must be reported as such — `KEYWORD_SELECTION.md` §12 K-7
commits to revisiting the keyword rather than tuning the threshold.

## 37. Long-form continuous-audio false-alarm test set

The set that measures the PS's actual requirement — "near-zero false activations" in continuous
listening. Everything else is secondary to this.

| Stream | Duration | Content | Keyword present? | Use |
|---|---|---|---|---|
| **CS-SWEEP** | **2 h** | val speakers + val noise + hard negatives | no | **choose the operating point** |
| **CS-VALIDATE** | **20 h** (min 10 h) | test speakers, unseen noise, unseen confusables | **no** | **report FA/hour — once** |
| **CS-DETECT** | **60 min** | 200 keyword utterances at **known timestamps**, natural gaps, realistic noise | yes | detection rate + latency |
| **CS-WILD** | **8 h** | unscripted real-room audio: conversation, music, TV, calls | no | ecological FA rate |
| **CS-INDIC** | **4 h** | Hindi/Tamil/Telugu/Bengali speech (Common Voice, CC0) | no | **क्ष exposure at natural frequency** |

**CS-INDIC is specific to this keyword.** क्ष occurs naturally in Indian-language speech; four
hours of it is the most honest FA test available for `Takshila`, and no other candidate keyword
would have needed it.

### Construction rules

1. **Concatenate real recordings** with realistic gaps and room tone — never zero-padding.
2. **No clip from any stream may appear in any training or clip-test set.** Streams draw from a
   reserved partition (leak L-10).
3. Ground truth is a **timestamp list**, not clip labels.
4. Fixed random seed; the file list is recorded in the manifest.
5. **CS-VALIDATE is opened once.** Every access is logged (leak L-9).

### What 10 h and 20 h can actually resolve — stated before measuring

False alarms are Poisson. If the true rate is **0.5 FA/h**:

| Observation window | Expected events | 95 % CI on the rate |
|---|---|---|
| 10 h | 5 | **0.16 – 1.17 FA/h** |
| 20 h | 10 | **0.24 – 0.92 FA/h** |
| 40 h | 20 | 0.31 – 0.77 FA/h |

**10 h gives an order of magnitude; 20 h gives a factor of ~2; a tight bound needs 40 h+.**
Any FA/h figure this project reports must carry its confidence interval and its observation
duration. "0 false alarms in 40 seconds" — the predecessor's longest negative run — is not a
measurement, and this table is why.

### Metrics produced

| Metric | From |
|---|---|
| **FRR** at fixed FA/h (0.5 and 1.0) | CS-DETECT vs CS-SWEEP/VALIDATE |
| **FA/hour** + Poisson CI | CS-VALIDATE, CS-WILD, CS-INDIC |
| **DET curve** (FRR vs FA/h across thresholds) | CS-SWEEP |
| **Detection rate per spoken keyword** | CS-DETECT |
| **Latency** (keyword end → decision → first packet → ASR receipt) | CS-DETECT timestamps |
| Precision / recall / F1, ROC/AUC | clip test set — **secondary diagnostic, always labelled** |
| Robustness by speaker / environment / distance / noise / volume / rate / variant | manifest breakdown fields |

---

# PART VI — DELIVERY

## Dataset architecture

```
              RAW (never deleted, never edited)
data/recordings/<speaker_id>/<session_id>/
        │   *.wav (unbounded length, H1 + H2 parallel)
        │   session.json, prompts.csv, rejected/
        ▼
   build_dataset.py   ── deterministic, seeded, re-runnable ──▶
        │  cut offsets · apply QC · assign splits · augment (train only)
        ▼
data/dataset/                          data/streams/
   manifests/*.csv                        cs_sweep/ cs_validate/ cs_detect/
   {train,validation,test}/               cs_wild/ cs_indic/
      {positive,near_homophone,           ground_truth/*.csv
       hard_negative,speech_negative,
       background,silence}/*.wav
        ▼
dataset_manifest/  (committed: counts + checksums, no audio)
```

**Raw is the source of truth; `dataset/` is a build artifact.** Any change to offsets, splits,
augmentation or QC is a rebuild, not a re-record. This is the direct fix for the predecessor's
inability to re-cut its positives.

## Directory structure

```
data/
├── recordings/                     # RAW — git-ignored, backed up separately
│   └── SPK007/S007_2026-10-02_E1/
│       ├── H1_u001.wav … H1_u068.wav
│       ├── H2_u001.wav … H2_u068.wav
│       ├── ambient_roomtone.wav
│       ├── session.json
│       ├── prompts.csv
│       └── rejected/
├── dataset/                        # BUILT — git-ignored, reproducible
│   ├── manifests/{train,validation,test}.csv
│   ├── LICENSES.md
│   ├── build_config.json
│   ├── train/{positive,near_homophone,hard_negative,speech_negative,background,silence}/
│   ├── validation/{…}/
│   └── test/{…}/                   # QUARANTINED
├── streams/                        # continuous audio
│   ├── cs_sweep/ cs_validate/ cs_detect/ cs_wild/ cs_indic/
│   └── ground_truth/*.csv
└── external/                       # public corpora, unmodified
    ├── librispeech/ common_voice/ speech_commands/ musan/ rirs_noises/
    └── SOURCES.md
dataset_manifest/                   # COMMITTED: manifest.json + CHECKSUMS.sha256
```

## Metadata format

- **Session:** `session.json` (schema §30, `schema_version` field mandatory)
- **Clips:** CSV manifests, one row per clip, columns per §30
- **Streams:** `ground_truth/<stream>.csv` — `stream_id, event_start_ms, event_end_ms, label, source_clip_id`
- **Fingerprint:** `dataset_manifest/manifest.json` + `CHECKSUMS.sha256`, committed to Git; audio never is
- **Provenance:** generated `LICENSES.md`

## Recording protocol

**Per session, ~20 minutes.** A fractional factorial — full crossing of 4 distances × 4
orientations × 4 volumes × 3 rates would be 192 utterances per speaker and is not collectable.

| Step | Content | Utterances | Time |
|---|---|---|---|
| 0 | Consent form, pseudonymous ID, metadata capture | — | 5 min |
| 1 | Level check + 60 s room tone | — | 2 min |
| **A** | **Core:** 1.0 m, on-axis, normal volume, 3 rates × 4 reps | 12 | 2 min |
| **B** | **Distance:** 0.3 / 2.0 / 3.0 m, on-axis, normal × 4 reps | 12 | 3 min |
| **C** | **Volume:** whisper / soft / loud at 1.0 m × 4 reps | 12 | 2 min |
| **D** | **Orientation:** 45° / 90° / 180° at 1.0 m × 4 reps | 12 | 3 min |
| **E** | **Hard negatives:** 20 prompts from §9 Tiers 1–3 | 20 | 3 min |
| **F** | **Free speech:** 60 s unscripted (→ `speech_negative`) | — | 1 min |
| | **Total** | **68** | **~21 min** |

**Rules:** prompts shown as written words, never played as audio (prevents mimicry); the
operator never corrects pronunciation; ≥ 1 s silence between takes; live QC (QC-3/4/7) with
immediate re-record on failure; each speaker records in **≥ 2 environments** across sessions.

## Collection script / tool requirements

| Tool | Requirement |
|---|---|
| `tools/record_session.py` | prompt-driven capture; H1+H2 simultaneous; live QC-3/4/7 with re-record; writes `session.json` + `prompts.csv`; resumable |
| `firmware/recorder/` | ESP32 sketch: I²S → 16 kHz mono → host over serial/Wi-Fi; asserts bit shift; reports its git SHA. **Needs B-1.** |
| `tools/annotate_keyword.py` | semi-automatic onset/offset marking (energy + /ʃ/ band detector), human-reviewed |
| `tools/build_dataset.py` | deterministic seeded build: cut offsets, QC, split, augment train-only, emit manifests; **fails on any §28 assertion** |
| `tools/build_streams.py` | assemble CS-* streams with ground-truth timestamps |
| `scripts/verify_dataset.py` | rebuild of the removed verifier, against the new schema |
| `scripts/generate_dataset_manifest.py` | rebuild of the fingerprint generator |
| `tools/audio_probe.py`, `audio_probe_bands.py` | **already exist and are dataset-agnostic** — use from the pilot onward |

## Public dataset sources that can legally supplement

Per §31: **LibriSpeech** (CC BY 4.0) · **Google Speech Commands** (CC BY 4.0) · **MUSAN**
(commercial-safe) · **OpenSLR-28 RIRs** (Apache 2.0) · **Mozilla Common Voice** (CC0, preferred,
and the source of Indian-English and Indic negatives). **ESC-50 is CC BY-NC 3.0 — avoid; record
our own environmental noise instead.** Piper TTS engine is GPL-3.0; log each voice model's own
licence.

## Exact human recordings we must collect ourselves

Nothing below can be sourced publicly — no corpus contains this keyword.

| # | Recording | Quantity | Why it cannot be substituted |
|---|---|---|---|
| 1 | **`Takshila` positives** | **30 speakers × 48 = 1,440** | the keyword is custom; no corpus has it |
| 2 | Hard negatives, human voices | 30 × 20 = 600 | must be our speakers, our rooms, our mic |
| 3 | Free speech, own speakers | 30 × 60 s = 30 min | speaker-matched negatives |
| 4 | Room tone, per environment | 6 × 5 min | our actual deployment rooms |
| 5 | Environmental noise | ~2 h | replaces NC-licensed ESC-50 |
| 6 | **EV-2 fresh-day re-record** | 3 speakers × 50 | catches session overfitting |
| 7 | **CS-DETECT** | 60 min, 200 timestamped utterances | ground truth for detection + latency |
| 8 | **CS-WILD** | 8 h unscripted | ecological FA rate |
| 9 | **EV-5 demo rehearsal** | 30 min | the actual demo conditions |

## Estimated collection effort

| Activity | Effort |
|---|---|
| Recorder firmware + `record_session.py` + pilot | **8–12 h** |
| Speaker recruitment (30, ≥ 6 L1 backgrounds) | 6–10 h |
| **30 sessions × 21 min** | **~11 h contact**, ~18 h with setup/turnover |
| Second environment for each speaker | +6 h |
| Environmental noise + room tone | 4 h |
| CS-WILD (8 h) + CS-DETECT (1 h) | 9 h capture, mostly unattended |
| Annotation + human review of onsets | 8–12 h |
| Build, QC, split, verify | 6 h |
| **Total** | **≈ 70–85 h**, of which ~35 h is live recording |

Realistically **2–3 weeks part-time with two people**, and it is **gated on B-1**. At the §33
minimum (15 speakers) this roughly halves to ~40 h.

## Exact next steps

1. **Resolve blocker B-1** — obtain the authoritative pin map, validate it against `HARDWARE.md`
   §3, wire the INMP441. *Nothing device-matched can be recorded until this is done.*
2. **A4/A5 bring-up** — board identity, I²S capture, measure the true sample rate, verify the
   24-in-32 bit shift.
3. **Build the recorder** — `firmware/recorder/` + `tools/record_session.py` with live QC.
4. **Run ONE pilot session** (operator as speaker), measure it with `tools/audio_probe.py` and
   `tools/audio_probe_bands.py`. **Exit bar:** format uniform, RMS in range, zero dropouts,
   keyword onset spread visible, ≤ 10 % reject rate.
5. **Fix whatever the pilot exposes**, then re-pilot. Only then recruit.
6. **Collect** — test speakers recorded and quarantined first.
7. **Build and verify** — `build_dataset.py`, all §28 assertions passing, fingerprint committed.
8. **Then** Phase B (features + parity) and Phase C (streaming harness) — **the harness before
   any model**, per D-005.

**Do not begin step 6 before step 4 passes.** A protocol fault found in a pilot costs one
session; found after 30 speakers it costs the project.
