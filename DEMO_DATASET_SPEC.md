# DEMO_DATASET_SPEC.md — Tier 1, demo-critical dataset

**Date:** 2026-09-09 · **Status:** active build target · **Window:** 12–16 h total build
**Keyword:** `Takshila` — **LOCKED** (D-011, sanity-checked in `KWS_ENGINE_DECISION.md` §5)
**Engine:** custom neural KWS on **TFLite Micro + ESP-NN** (D-012)

> **This is the dataset we build now.** The 30-speaker / 20-hour programme is preserved
> unchanged as a post-demo target in **`RESEARCH_DATASET_ROADMAP.md`** and **does not block
> this build**.
>
> The scientific rigour of the Tier-2 spec is **retained in full here** — leakage controls,
> metadata schema, hard-negative strategy, continuous-audio evaluation and reproducibility are
> **not** relaxed. Only *scale* is reduced. A small dataset built correctly is defensible; a
> large one built carelessly is not.

---

## 0a. AMENDMENT 2026-09-10 — one speaker, not six

> **This spec assumed 6 human speakers. Exactly one is available.** That is not a smaller
> version of the same plan — it changes which techniques are viable, so the positive strategy
> was rebuilt around **synthetic voice diversity** with real audio reserved for evaluation.
>
> | | This spec assumed | Actually built |
> |---|---|---|
> | Human speakers | 6 | **1** |
> | Positive source | real recordings | **~1,090 Piper TTS voices** (incl. L2-ARCTIC non-native English + native Indic) |
> | Real positives | ~240 | **14 recordings** → validation/test only |
> | Test positives | 40 (±9.5 pp) | **~7 independent utterances (±35 pp)** |
> | Speaker-disjoint split | yes | **impossible** — substitute is session-disjoint |
>
> **Everything methodological in this document still holds** — partial-keyword negatives,
> offset-sampling-is-not-augmentation, recorded-not-mixed test conditions, the leakage
> assertions, the metadata schema, the QC thresholds. Only the *source* of positive diversity
> changed, and the honesty obligations got stricter, not looser.
>
> Design and evidence: `docs/DATASET_RESEARCH.md` · sizing: `DATASET_SIZE_RATIONALE.md` ·
> implementation: `DATASET_FACTORY.md` · decision: `DECISIONS.md` D-014.

## 0. Time budget

Of the 12–16 h build, **data work gets ~3.5 h**. Everything below is sized to that.

| Activity | Budget |
|---|---|
| Recorder firmware + capture tool | 1.0 h |
| **Human recording sessions (all speakers)** | **1.5 h** |
| Ambient / background capture | 0.5 h (mostly unattended) |
| Public-corpus fetch + stream assembly | 0.5 h (mostly compute) |
| Build, QC, verify | 0.5 h |

Synthetic hard-negative generation runs **unattended in parallel** and costs no wall-clock.

---

## 1. Positive utterances

| | Target | **Minimum** |
|---|---:|---:|
| Speakers | **6** | **3** |
| Utterances per speaker | 40 | 30 |
| **Raw positive utterances** | **240** | **90** |
| After offset sampling (×6) | 1,440 | 540 |
| After train augmentation (×4, train split only) | ~4,300 | ~1,600 |

**Per-speaker session — 12 minutes, 40 utterances.** A compressed fractional factorial; the
Tier-2 68-utterance protocol does not fit the window.

| Block | Condition | Utterances |
|---|---|---:|
| A | 1.0 m, on-axis, normal volume, **3 rates** (slow ≤850 ms / normal / fast) | 12 |
| B | **0.3 m / 2.0 m / 3.0 m**, on-axis, normal | 9 |
| C | **whisper / soft / loud** at 1.0 m | 9 |
| D | **45° / 90°** off-axis at 1.0 m | 6 |
| E | Pronunciation variants: **V3** (fast `kshee-laa`) ×2, **V7** (`Taxila`) ×2 | 4 |
| | **Total** | **40** |

**The slow rate is prompted as "deliberate, not drawn out."** Takes measuring > 880 ms are
flagged `duration_over_window=true` and excluded from positives — see
`KWS_ENGINE_DECISION.md` §4.

## 2. Number of speakers — and the honesty requirement

**Target 6. Absolute minimum 3.**

| Speakers | Split | Test positives | 95 % CI on detection rate |
|---:|---|---:|---|
| 6 | 4 train / 1 val / **1 test** | 40 | **± 9.5 pp** |
| 4 | 2 / 1 / **1** | 40 | ± 9.5 pp |
| 3 | 2 / — / **1** (val = train subset by session) | 40 | ± 9.5 pp, **no clean val** |

> ### ⚠ Declare this, do not bury it
> With 6 speakers the model is **speaker-dependent-leaning**. **No speaker-independence claim
> may be made**, on a slide, in a README, or to a judge. The demo states the speaker count and
> the confidence interval. Getting caught by a judge whose voice fails is far worse than saying
> in advance that the corpus is small — and `RESEARCH_DATASET_ROADMAP.md` is the answer to
> "what would you do with more time".

Recruit for **≥ 3 distinct L1 backgrounds** and **both genders** even at 6 speakers; diversity
per speaker is free, speakers are not.

## 3. Real INMP441 recordings

**100 % of human positives must be captured through the INMP441 on the ESP32-S3.**

At this dataset size, device match is the **only** domain advantage available — the corpus is
too small to generalise across microphones, so it must not have to.

| Requirement | Value |
|---|---|
| Capture path | INMP441 → I²S 24-in-32 → **upper 16 bits** → 16 kHz mono int16 |
| Verification | `i2s_shift_verified` asserted per session (QC-8) |
| Parallel reference | laptop/phone mic recording simultaneously — **insurance only**, not training data |
| Ambient / background | **also INMP441**, in the demo room |

> ### 🔴 HARD DEPENDENCY: blocker B-1 (pin map)
> **No INMP441 recording is possible until the mic is wired.** This is the first action of the
> build, ahead of everything else.
>
> **If B-1 is still unresolved at T+2 h:** fall back to laptop-mic capture, apply a band-limit
> augmentation approximating the INMP441 response, and label every affected clip
> `device_simulated=true`. **This is materially worse** — it reintroduces the domain gap the
> device-matched corpus exists to remove — and it must be stated in the demo.

## 4. Hard negatives

| Source | Items | Voices | Clips |
|---|---|---|---:|
| **Human** — each speaker reads 12 prompts from `DATASET_SPEC.md` §9 Tiers 1–2 | 12 | 6 | 72 |
| **Synthetic (Piper TTS)** — the full 74-item list | **74** | **≥ 12** | **~2,200** |
| **Public** — Speech Commands + Common Voice segments containing क्ष | — | many | ~600 |

**Priority order if time runs short:** Tier 1 (क्ष family) → Tier 2 (/tæks/) → Tier 4 (full-word
neighbours, incl. `Takshashila`) → Tier 3 → Tier 5.

**Tiers 1 and 2 go in `train`.** The predecessor shipped its three hardest confusables in
validation/test only; that mistake is not repeated at any scale.

Synthetic hard negatives are used **without reservation** — we need the model to reject a
*phone sequence*, and a TTS "shiksha" contains the क्ष conjunct genuinely
(`KWS_ENGINE_DECISION.md` §6).

## 5. Partial-keyword windows

**Target ≥ 480 · Minimum ≥ 180.** Derived, not spoken: **2 partial windows per raw positive
utterance** at 25–75 % keyword coverage, labelled `hard_negative/partial`.

**This is the single highest-value negative class and is not optional at any scale.** Their
absence made a deployed model fire on **49.7 %** of realistic sliding windows while its curated
clip set reported **10.7 %** `[prior-build]`.

## 6. Unknown speech

| Source | Licence | Clips |
|---|---|---:|
| **Mozilla Common Voice, Indian English filtered** | **CC0** | 3,000 |
| LibriSpeech `train-clean-100` subset | CC BY 4.0 | 2,500 |
| Google Speech Commands | CC BY 4.0 | 1,500 |
| Common Voice Hindi / Tamil / Telugu | CC0 | 1,500 |
| Own free speech (60 s per speaker) | own | 300 |
| **Total** | | **~8,800** |

Indic speech is included deliberately: क्ष occurs naturally in Indian-language speech, so it
carries hard negatives no script can invent.

## 7. Silence

| Sub-label | Source | Clips |
|---|---|---:|
| `silence/roomtone_quiet` | **INMP441, demo room** | 400 |
| `silence/roomtone_hvac` | **INMP441, fan/AC on** | 400 |
| `silence/digital` | synthesised zero + dither | 100 |
| **Total** | | **900** |

Real room tone dominates: the device idles in the demo room, not in digital silence.

## 8. Background / environmental noise

| Sub-label | Source | Clips |
|---|---|---:|
| `background/hvac`, `impact`, `electronic` | **own INMP441 recording, 20 min** | 1,200 |
| `background/music` | **MUSAN music** | 800 |
| `background/crowd` | MUSAN + own | 800 |
| `background/outdoor` | MUSAN noise | 400 |
| **Total** | | **3,200** |

**ESC-50 is not used** — CC BY-NC 3.0. MUSAN and our own recordings replace it (§15).

## 9. Continuous false-alarm audio

The metric the PS actually grades. **Cheap in wall-clock**: assembled from public corpora by
concatenation, plus ambient that records itself while we work.

| Stream | Target | Minimum | Content | Keyword? |
|---|---:|---:|---|---|
| **CS-SWEEP** | 1 h | 30 min | val speaker + val noise + hard negatives | no |
| **CS-VALIDATE** | **6 h** | **3 h** | test speaker, unseen noise, unseen confusables, Common Voice | **no** |
| **CS-INDIC** | 2 h | 1 h | Hindi/Tamil/Telugu (Common Voice, CC0) — **natural क्ष exposure** | no |
| **CS-WILD** | 2 h | 1 h | **INMP441 left recording in the room while we work** | no |
| **CS-DETECT** | 15 min | 10 min | **60 keyword utterances at known timestamps**, natural gaps | **yes** |

### What these durations can actually resolve — before measuring

False alarms are Poisson. At a true rate of **0.5 FA/h**:

| Window | Expected events | 95 % CI |
|---|---:|---|
| **3 h (minimum)** | 1.5 | **0.10 – 1.83 FA/h** |
| **6 h (target)** | 3 | **0.16 – 1.46 FA/h** |
| 20 h (Tier 2) | 10 | 0.24 – 0.92 FA/h |

**A Tier-1 FA/h figure is an order-of-magnitude statement, not a number.** It must always be
reported with its CI and its observation duration. "Zero false alarms in 3 hours" means "below
roughly 1.2 FA/h with 95 % confidence" — say that, not "zero".

## 10. Train / validation / test split

| Split | Speakers | Purpose | May tune on? |
|---|---|---|---|
| `train` | 4 | fit weights | yes |
| `validation` | 1 | early stopping, **threshold sweep** | yes |
| `test` | **1, quarantined** | **final evaluation, once** | **NO** |

Public negatives are split by **their own** speaker IDs. TTS negatives are split by `voice_id`.
The threshold is chosen on `validation` / CS-SWEEP and reported on `test` / CS-VALIDATE.

## 11. Speaker separation

**No speaker appears in more than one split. No exceptions.** With 6 speakers this costs a
sixth of the corpus, and it is still non-negotiable — a test split sharing speakers with train
measures memorisation, and there would be no way to know.

Test speaker is **chosen and recorded first**, then quarantined before any training.

## 12. Evaluation-only audio

| Set | Content | Size |
|---|---|---|
| **EV-1** | held-out speaker, full session | 40 positives |
| **EV-2** | **2 training speakers re-recorded ≥ 2 h later, different room/position** | 30 positives |
| **EV-3** | 74-item confusable list, **TTS voices unseen in train** | ~400 clips |
| **EV-5** | **demo rehearsal — actual room, actual distances, actual script** | 15 min |

**EV-2 is disproportionately important at this scale.** With one test speaker, session
overfitting is the likeliest silent failure, and same-speaker-different-session is the control
that catches it. It is an *evaluation* set and never enters training — the only justified
same-speaker crossing.

## 13. Metadata

**The Tier-2 schema is retained unchanged** (`DATASET_SPEC.md` §30) — `session.json` plus
per-clip manifest rows. Fields are cheap; regret is not. Mandatory at Tier 1:

`clip_id` · `filepath` · `class` · `sub_label` · `model_target` · **`speaker_id`** ·
**`session_id`** · **`source_utterance_id`** · `variant` · `keyword_onset_ms` /
`keyword_offset_ms` / `keyword_coverage` · `distance_m` · `orientation_deg` · `volume` · `rate` ·
`environment_id` · `snr_db` · `device_id` · **`device_simulated`** · `augmentation` ·
**`split`** · `source_corpus` · `source_license` · `sha256` · `qc_status` ·
**`duration_over_window`**

The three bolded split/lineage keys are what make §14 enforceable.

## 14. Augmentation

**The Tier-2 distinction is preserved exactly:**

- **Offset sampling is NOT augmentation.** It is the real inference distribution → applied to
  **train, validation and test**.
- **Augmentation** synthesises unseen conditions → **train only**.

| Technique | Parameters | Split |
|---|---|---|
| Offset sampling | 6 windows/utterance + 2 partials | all |
| Additive noise | SNR −5…30 dB, **train noise partition only** | train |
| RIR convolution | OpenSLR-28, RT60 0.2–1.5 s | train |
| Gain | −12…+6 dB | train |
| Time stretch | 0.9–1.1×, pitch preserved | train |
| SpecAugment | ≤2 freq / ≤2 time masks | train |
| INMP441 band-limit | on public + any `device_simulated` audio | train |

**Hard rules, unchanged from Tier 2:**
1. **The test split is never augmented.**
2. An augmented clip **inherits its source's split** (enforced via `source_utterance_id`).
3. Train mixes **train-partition noise only**.
4. **Augmentation multiplies clips, not information.** Capped at **×4 on positives**; the raw
   speaker count (6) remains the figure of record on every slide.

## 15. Data provenance

| Source | Licence | Commercial | Use |
|---|---|---|---|
| **Own INMP441 recordings** | project-owned, consented | ✅ | positives, negatives, ambient, streams |
| **Mozilla Common Voice** | **CC0** | ✅ | unknown speech, Indic, streams — **preferred** |
| LibriSpeech | CC BY 4.0 | ✅ | unknown speech |
| Google Speech Commands | CC BY 4.0 | ✅ | short-command negatives |
| MUSAN | CC / public domain, commercial-safe | ✅ | music, noise, babble |
| OpenSLR-28 RIRs | Apache 2.0 | ✅ | reverb augmentation |
| Piper TTS | engine **GPL-3.0**; **log each voice model's own licence** | ⚠ | hard negatives; positives only A/B-gated |
| **ESC-50** | **CC BY-NC 3.0** | ❌ | **NOT USED** |

`LICENSES.md` is generated at build time. Written consent from every speaker; pseudonymous IDs;
**no real names, no minors**.

## 16. Quality-control thresholds

**All 15 Tier-2 QC rules apply unchanged** (`DATASET_SPEC.md` §29). The four that must run
**live during capture**, because re-recording later is impossible at this scale:

| # | Rule | Threshold | Action |
|---|---|---|---|
| **QC-3** | Clipping | < 0.1 % full-scale samples | **re-record now** |
| **QC-4** | Level | −40 ≤ RMS ≤ −6 dBFS | **re-record now** |
| **QC-7** | Dropouts | no > 20 ms zero-gap mid-utterance | **re-record now** — I²S/DMA loss |
| **QC-8** | Bit alignment | plausible dynamic range | **stop the session** — the 48 dB shift error |

Plus at build time: QC-1 length exactly 16,000 samples · QC-2 format · QC-9 keyword completeness
→ reclassify as partial · QC-10 V9 `Takshashila` → reclassify as `near_homophone` · QC-13
duplicate SHA-256 · QC-14 keyword duration 300–880 ms.

**Rejects are archived with a reason, never deleted.** Target reject rate ≤ 10 %; higher means
fix the room or the protocol, not the data.

---

## 17. Minimum data required before the FIRST training experiment

Not the full Tier-1 target — the smallest set that makes a **first honest training run**
meaningful. Aim to reach this at **T+4 h**.

| Class | Minimum for first run |
|---|---:|
| Positive raw utterances | **90** (3 speakers × 30) |
| → after offset sampling | 540 |
| `hard_negative/partial` | 180 |
| `near_homophone` (Tiers 1–2, TTS) | 600 |
| `speech_negative` | 2,000 |
| `background` + `silence` | 1,000 |
| **Held-out test speaker** | **1, quarantined** |
| CS-SWEEP | 30 min |
| CS-DETECT | 10 min |

**Below this, do not train** — a run on less will produce a number that means nothing and will
cost more time in false confidence than it saves.

## 18. Build order — what to collect first

Ordered so that the **most irreplaceable** data is captured earliest.

| # | Step | Why this order |
|---|---|---|
| 1 | **Resolve B-1, wire INMP441, verify bit shift (QC-8)** | nothing device-matched exists without it |
| 2 | **Record the TEST speaker first**, quarantine immediately | if time runs out, the held-out set still exists |
| 3 | Start CS-WILD recording in the room — **runs unattended all day** | free data, accumulates while we work |
| 4 | Start Piper hard-negative generation — **runs unattended** | no wall-clock cost |
| 5 | Record remaining 5 speakers (12 min each) | the irreplaceable human data |
| 6 | Record ambient/background, 20 min | |
| 7 | Fetch public corpora, assemble streams | mostly compute |
| 8 | Build, QC, verify, fingerprint | |

**Steps 3 and 4 start early and cost nothing** — begin them before step 5, not after.

---

## What must be recorded on the actual INMP441

| # | Recording | Quantity | Substitutable? |
|---|---|---|---|
| 1 | **`Takshila` positives** | 6 speakers × 40 = **240** | **No** — no corpus contains this keyword |
| 2 | Human hard negatives | 6 × 12 = 72 | No — device + room match |
| 3 | Free speech, own speakers | 6 × 60 s | No |
| 4 | Room tone (quiet + HVAC) | 10 min | No — the demo room specifically |
| 5 | Environmental noise | 20 min | No — replaces NC-licensed ESC-50 |
| 6 | **CS-WILD ambient** | 2 h unattended | No |
| 7 | **CS-DETECT timestamped** | 15 min, 60 utterances | No — ground truth for detection + latency |
| 8 | EV-2 re-record | 2 speakers × 15 | No |
| 9 | EV-5 demo rehearsal | 15 min | No |

## What can be sourced from public licensed datasets

| Need | Source | Licence | Effort |
|---|---|---|---|
| Unknown speech, accent-diverse | **Common Voice (Indian English)** | **CC0** | download |
| Unknown speech, read | LibriSpeech | CC BY 4.0 | download |
| Short-command negatives | Speech Commands | CC BY 4.0 | download |
| Indic speech / natural क्ष | Common Voice hi/ta/te | CC0 | download |
| Music, babble, noise | MUSAN | commercial-safe | download |
| Reverb | OpenSLR-28 RIRs | Apache 2.0 | download |
| Long-form FA streams | assembled from the above | inherited | concatenation |
| Synthetic hard negatives | Piper TTS | GPL-3.0 engine, per-voice models | unattended generation |

**Nothing containing the keyword can be sourced.** Every positive is ours to record.
