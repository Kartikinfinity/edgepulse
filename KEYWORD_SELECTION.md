# KEYWORD_SELECTION.md — scientific selection of the custom wake keyword

**Date:** 2026-09-09 · **Status:** research complete · **KEYWORD CONFIRMED: `Takshila`**
Recorded as binding decision **D-011**. **Nothing has been trained. No dataset has been collected.**

This document delivers the 15 required outputs. Every external claim carries a source.
Where a number is a *prediction* rather than a *measurement*, it is labelled as such — no
false-alarm rate in this document has been measured, because no data exists yet.

---

## 1. Research summary

### 1.1 What the problem statement actually requires

From `PS26172` (audit in the prior research base, corroborated against the portal text):

| Clause | Requirement |
|---|---|
| C11 | **"Training must be done on a custom keyword."** Models pre-trained on generic smart-assistant keywords are banned. |
| C15 | "Model must work for **the given** custom keyword" — singular. No multi-keyword requirement. |
| C7 | "High true-positive rate with **near-zero false activations**" — unquantified. |
| C12 | `<256 KB RAM`, `<10 % CPU idle` — **out of scope this phase by user instruction**. |

**Consequence for keyword choice:** the PS constrains us to *a* custom keyword and gives no
further guidance. The choice is therefore ours to make on engineering grounds, and the only
graded property it touches directly is **near-zero false activations** — which makes
**false-alarm resistance the dominant selection criterion.**

### 1.2 What the wake-word literature says

| Finding | Source |
|---|---|
| **≥ 6 phonemes.** "Choosing a wake phrase with fewer than six phonemes is not recommended, because it is harder to detect and more likely to produce false positives." "Alexa" has 6; "OK Google" has 8. | Picovoice |
| **2–4 syllables**, with 3–4 giving enough acoustic information without being cumbersome. | Picovoice, Sensory |
| **Phonetic variety matters more than length alone.** "Pick a phrase that has a variety of different sounds. Different phonemes create a more distinct signature and are less likely to create false alarms." | Picovoice |
| **Plosives, affricates and fricatives** (/k/, /g/, /tʃ/) separate better from background noise; distinct vowel patterns aid acoustic separation. | Sensory, Picovoice |
| **Avoid names, common commands, and everyday-conversation phrases** — they cause unintended activations. | Picovoice |
| **False alarms concentrate on specific phonetic snippets, not whole-word similarity.** FakeWake identified "decisive factors" — e.g. the *ks* in *Alexa* — and showed that **Levenshtein distance fails to predict which words falsely trigger**. Detectors relying on **fewer distinctive phonetic elements produced significantly more fuzzy words**. | FakeWake (arXiv 2109.09958) |
| Real systems have large fuzzy-word sets: **130 for Echo Dot, 322 for AliGenie**; **>40 %** of fuzzy words survive changes in volume, speed and noise. | FakeWake |
| An Echo Dot reliably reacted to **89 words**, some phonetically distant from "Alexa" ("alachah", "lechner", "electrotelegraphic"). | Schönherr et al. 2020 |
| Amazon's own wake-word evaluation patent scores candidates by **how often the candidate's phone sequence appears in general speech**. | US9275637B1 |

**Two conclusions follow, and they drive everything below:**

1. **Maximise the number of *distinct* phonetic elements**, not merely length. FakeWake shows
   sparse-feature detectors are the ones that misfire.
2. **Edit distance is not a safe screen for hard negatives.** Confusables must be derived from
   *shared phonetic snippets*, particularly the onset and the stressed syllable.

### 1.3 What Espressif requires — and why we cannot meet it

Espressif's official WakeNet customization specification:

| Requirement | Value |
|---|---|
| Wake word length | **3–6 "symbols"** (syllables) |
| Speakers | **> 500**, men and women of all ages, **≥ 100 children** |
| Corpus size | **≥ 20,000 qualified entries** |
| Environment | quiet room **< 40 dB**, professional audio room recommended, hi-fi microphone |
| Protocol | at **1 m and 3 m**, 15 repetitions each (5 fast / 5 normal / 5 slow) |
| Audio | 16 kHz, 16-bit signed, mono, WAV |
| Turnaround | 2–3 weeks, **paid service** |

**This is unreachable for this project**, and saying so plainly matters more than pretending
otherwise. It is also *informative*: it tells us the industrial bar for a production wake word
is ~500 speakers, so a student project with tens of speakers must **buy back robustness through
keyword choice** — the one lever that is free. A keyword with more distinct phonetic elements
needs less data to reach the same false-alarm rate.

Note also that WakeNet itself is **not** our path: it is a pre-trained Espressif model family,
and C11 requires training on a custom keyword. We use its *specification* as evidence about
what a good wake word looks like, not its models. Its 16 kHz / 16-bit / mono / WAV format
requirement is worth adopting verbatim since it matches our INMP441 capture path exactly.

### 1.4 Indian English phonology — hard constraints on the candidate space

Our speakers will be Indian English speakers. Published phonological descriptions give four
constraints that **eliminate** candidate keywords rather than merely scoring them down:

| Feature | Consequence for keyword design |
|---|---|
| **/v/ ~ /w/ merge** — "wet" and "vet" can sound alike | **Reject any keyword whose identity depends on /v/ or /w/.** |
| **Dental fricatives /θ, ð/ → stops [t̪, d̪]** | **Reject any keyword containing "th".** |
| **Vowel inventory is smaller** — English's ~15 vowels merge into fewer | **Use maximally separated vowels** (/aː/, /iː/, /eː/, /oː/); never rely on a fine distinction such as /æ/ vs /ɛ/. |
| **Consonant clusters simplified** — vowel epenthesis before initial clusters, deletion of final clusters | **Reject onset/coda clusters.** Prefer open CV syllables. |
| Retroflex realisation of /t, d/ | Harmless — it is *consistent* within and across Indian speakers, so it does not add variance. |

**A fifth, project-specific constraint** comes from our own microphone. The INMP441 is
−3 dB at 60 Hz and 15 kHz, and the prior build measured **64.6 % of its noise energy below
100 Hz** with the cleanest region in the 4–8 kHz band `[prior-build]`. Sibilants and affricates
(/ʃ/, /s/, /tʃ/) put energy exactly there. **A keyword carrying sibilant energy is matched to
this specific microphone's best band** — a hardware-driven argument, not an aesthetic one.

### 1.5 One word, two words, or a phrase? — resolved on our own architecture

| Option | Assessment |
|---|---|
| **1–2 syllables** | **Rejected.** Below the 6-phoneme floor; highest false-alarm risk. |
| **One word, 3–4 syllables** | **Selected.** 7–9 phonemes clears the floor; ~0.5–0.7 s of speech fits comfortably inside the **49 × 13 = 1.0 s** model input already fixed in `ARCHITECTURE.md` §3. |
| **Two words ("Hey X")** | Rejected **on a concrete architectural ground**: a carrier + 3-syllable word runs ~1.0–1.2 s and **does not fit the 1.0 s context window**. Adopting it would force a larger input, and the prior build measured a 98×40 input at **2,240 ms/inference vs 84.17 ms** for 49×13 — a 26.6× penalty `[prior-build]`. It would also add carrier-word latency to the SIH-graded metric. |
| **Longer phrase** | Rejected — poor UX, worse latency, no FA benefit over a well-chosen single word. |

**Decision: one word, 3–4 syllables, 7–9 phonemes.** This is the first place the answer is
driven by *our* system rather than by generic advice.

---

## 2. Candidate keyword table

18 candidates spanning four strategies. IPA is broad, in the Indian English realisation.

| # | Candidate | Strategy | IPA (Indian English) | Syll | Phonemes | Notes |
|---|---|---|---|---|---|---|
| 1 | **Takshila** | Heritage, invented-adjacent | /t̪əkˈʃiː.laː/ | 3 | 7 | ancient seat of learning |
| 2 | **Chetaki** | Invented, Indic phonotactics | /tʃeːˈt̪ə.kiː/ | 3 | 6 | — |
| 3 | **Sanjika** | Invented | /sənˈdʒiː.kaː/ | 3 | 7 | — |
| 4 | **Shalaka** | Sanskrit (rod/probe), rare | /ʃəˈlaː.kaː/ | 3 | 6 | — |
| 5 | **Chatika** | Pure invention | /tʃəˈt̪iː.kaː/ | 3 | 6 | — |
| 6 | **Nakshatra** | Sanskrit (star/constellation) | /nəkˈʃət̪.rə/ | 3 | 8 | space-topical |
| 7 | **Antariksh** | Hindi (space) | /ən.t̪əˈrikʃ/ | 3 | 8 | space-topical |
| 8 | **Vyoma** | Sanskrit (sky) | /ˈʋjoː.maː/ | 2 | 5 | ISRO's Vyommitra |
| 9 | **Kalpana** | Name (Kalpana Chawla) | /ˈkəl.pə.naː/ | 3 | 7 | real person |
| 10 | **Chandrika** | Sanskrit (moonlight) / name | /tʃənˈd̪ri.kaː/ | 3 | 8 | — |
| 11 | **Tejaska** | Invented from *tejas* | /t̪eːˈdʒəs.kaː/ | 3 | 7 | HAL Tejas |
| 12 | **Kanishka** | Historical name | /kəˈniʃ.kaː/ | 3 | 7 | AI-182 association |
| 13 | **Suraksha** | Hindi (safety) | /suˈrək.ʃaː/ | 3 | 7 | common word |
| 14 | **Sanketa** | Sanskrit (**signal**) | /sənˈkeː.t̪aː/ | 3 | 7 | *Sanket* = common name |
| 15 | **Solvani** | **Deprecated incumbent** | /sɔlˈʋaː.ni/ | 3 | 7 | evaluated for completeness |
| 16 | **Orbita** | Latinate, brandable | /ˈɔr.bi.t̪aː/ | 3 | 7 | ≈ "orbiter" |
| 17 | **Hey Takshila** | Two-word control | /heː t̪əkˈʃiː.laː/ | 4 | 9 | window-length control |
| 18 | **Go** | Deliberate bad control | /goː/ | 1 | 2 | sanity check on the rubric |

---

## 3. Candidate scoring matrix

### 3.1 Rubric and an honest note on which criteria discriminate

All 20 requested criteria (A–T) were assessed. **Four of them do not discriminate between
candidates and are reported as constant rather than padded with invented variation:**

- **L (ESP32-S3 compatibility)** — every 3–4 syllable candidate uses the identical
  I²S → MFCC → 49×13 int8 DS-CNN path. Constant **5/5** for candidates 1–16.
- **M (custom KWS model suitability)** — likewise constant for 1–16; the model does not care
  which word it is trained on, only how separable it is (captured by A and E).
- **N (SIH problem relevance)** — the PS requires only that the keyword be *custom*. Every
  candidate except a pre-trained assistant keyword satisfies it. Constant **5/5**.
- **R (cloud ASR transition clarity)** — determined by the pipeline's pre-roll and
  end-of-keyword timestamping, not by the word. Weakly varies only with offset crispness,
  folded into K.

Scoring is **1–5, higher is better**, against these weights:

| Weight | Criteria | Rationale |
|---|---|---|
| **×3** | A (phonetic distinctiveness), C (similarity to common words), E (accidental activation), S (data-collection feasibility) | A/C/E drive the one graded property the PS names — near-zero false activations. S decides whether the project is deliverable at all. |
| **×2** | B (syllable/phoneme structure), D (homophones), F (Indian-English ease), G (accent robustness), K (continuous-KWS suitability), T (licensing/branding) | Second-order drivers of FRR/FAR and of legal risk. |
| **×1** | H (fast speech), I (soft speech), J (consistency), O (ISRO relevance), P (memorability), Q (product identity) | Real but subordinate; O/P/Q are presentation, not performance. |

### 3.2 Matrix

| # | Candidate | A×3 | B×2 | C×3 | D×2 | E×3 | F×2 | G×2 | H | I | J | K×2 | O | P | Q | S×3 | T×2 | **Total** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Takshila** | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 5 | 5 | 4 | 5 | 5 | 5 | 4 | **149** |
| 2 | **Chetaki** | 4 | 4 | 4 | 3 | 3 | 5 | 5 | 4 | 4 | 5 | 5 | 3 | 4 | 4 | 5 | 4 | **129** |
| 3 | **Sanjika** | 5 | 4 | 4 | 3 | 3 | 5 | 5 | 4 | 4 | 5 | 5 | 3 | 4 | 4 | 5 | 5 | **134** |
| 4 | **Shalaka** | 4 | 4 | 4 | 4 | 4 | 5 | 5 | 4 | 4 | 5 | 4 | 3 | 3 | 3 | 5 | 4 | **130** |
| 5 | **Chatika** | 4 | 4 | 5 | 4 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | 2 | 3 | 3 | 5 | 5 | **132** |
| 6 | Nakshatra | 5 | 5 | 3 | 4 | **2** | 3 | 3 | 3 | 3 | 3 | 4 | 5 | 5 | 5 | 5 | 4 | 120 |
| 7 | Antariksh | 5 | 5 | 2 | 4 | **1** | 3 | 3 | 3 | 3 | 3 | 3 | 5 | 5 | 5 | 5 | 4 | 110 |
| 8 | Vyoma | 3 | **2** | 3 | 3 | 3 | **2** | **2** | 3 | 3 | 3 | 3 | 5 | 4 | 4 | 5 | **2** | 96 |
| 9 | Kalpana | 4 | 4 | **2** | 3 | **2** | 5 | 4 | 4 | 4 | 4 | 4 | 5 | 5 | 4 | 5 | **2** | 111 |
| 10 | Chandrika | 4 | 5 | 3 | 3 | 3 | 4 | 4 | 3 | 3 | 4 | 4 | 3 | 4 | 4 | 5 | 3 | 120 |
| 11 | Tejaska | 5 | 4 | 4 | 3 | 3 | 5 | 4 | 4 | 4 | 4 | 5 | 4 | 4 | 4 | 5 | **2** | 126 |
| 12 | Kanishka | 5 | 4 | 4 | 3 | 3 | 5 | 5 | 4 | 4 | 5 | 5 | 2 | 3 | **1** | 5 | **2** | 124 |
| 13 | Suraksha | 4 | 4 | **2** | 3 | **2** | 4 | 4 | 3 | 3 | 4 | 4 | 3 | 3 | 3 | 5 | 4 | 107 |
| 14 | Sanketa | 5 | 4 | 3 | **2** | **2** | 5 | 5 | 4 | 4 | 5 | 5 | 4 | 4 | 4 | 5 | 3 | 119 |
| 15 | **Solvani** | 3 | 4 | **2** | **1** | **2** | **2** | **2** | 3 | 3 | 3 | 4 | 2 | 3 | 3 | 5 | 4 | **95** |
| 16 | Orbita | 3 | 4 | **2** | **2** | 3 | 4 | 3 | 3 | 3 | 4 | 4 | 4 | 4 | 4 | 5 | 3 | 105 |
| 17 | Hey Takshila | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 5 | **1** | 4 | 4 | 4 | 4 | 4 | 137 |
| 18 | Go | **1** | **1** | **1** | **1** | **1** | 5 | 4 | 2 | 2 | 4 | **1** | 1 | 1 | 1 | 5 | 3 | **58** |

The "Go" control scores 58 against Takshila's 149 — the rubric separates a deliberately awful
keyword from a good one by ~2.5×, which is the minimum sanity check a scoring scheme should pass.

---

## 4. Phonetic analysis

### 4.1 Why the top candidate's structure is favourable

**Takshila** /t̪əkˈʃiː.laː/ — 7 phonemes, 3 syllables, structure **CVC·CV·CV**.

| Position | Segment | Manner class | Contribution |
|---|---|---|---|
| onset | /t̪/ | dental stop | sharp transient; clean onset for the detector |
| — | /ə/ | central vowel | unstressed, low information (accepted) |
| coda 1 | /k/ | velar stop | second transient; **burst spectrum distinct from /t̪/** |
| onset 2 | /ʃ/ | postalveolar fricative | **sustained 3–8 kHz energy — the INMP441's cleanest band** |
| — | /iː/ | close front vowel | maximally separated from /aː/ |
| onset 3 | /l/ | lateral approximant | clear formant transition |
| — | /aː/ | open back vowel | maximally separated from /iː/; crisp offset for timestamping |

**Four distinct manner classes** (stop, fricative, lateral, vowel) and **five distinct places of
articulation**. This is precisely the "variety of different sounds" Picovoice prescribes and the
opposite of the sparse-feature detectors FakeWake found most vulnerable.

**Vowel sequence /ə/ → /iː/ → /aː/** spans the vowel space corners. It survives the Indian
English vowel-merger constraint because no two of its vowels are ever confused.

**The /kʃ/ juncture** deserves comment. In English it is an awkward cluster, but in Indian
languages **क्ष is a single native conjunct** occurring in everyday words (*rakshak*,
*shiksha*, *lakshya*). For our speaker population it is not a cluster requiring epenthesis —
it is one familiar unit. **This is an advantage available only because the speakers are Indian**,
and it simultaneously makes the word *harder* for a general-English false trigger to produce.

### 4.2 Constraint compliance across the shortlist

| Candidate | ≥6 phonemes | 3–4 syll | No /v~w/ | No /θ,ð/ | No problem cluster | Distinct vowels | Sibilant energy | Obstruent onset |
|---|---|---|---|---|---|---|---|---|
| **Takshila** | ✅ 7 | ✅ 3 | ✅ | ✅ | ✅ (native conjunct) | ✅ ə-iː-aː | ✅ /ʃ/ | ✅ /t̪/ |
| **Sanjika** | ✅ 7 | ✅ 3 | ✅ | ✅ | ✅ | ✅ ə-iː-aː | ✅ /s/,/dʒ/ | ✅ /s/ |
| **Chetaki** | ✅ 6 | ✅ 3 | ✅ | ✅ | ✅ | ⚠ eː-ə-iː | ✅ /tʃ/ | ✅ /tʃ/ |
| Nakshatra | ✅ 8 | ✅ 3 | ✅ | ✅ | ❌ /tr/ coda | ⚠ ə-ə-ə | ✅ /ʃ/ | ⚠ nasal |
| Antariksh | ✅ 8 | ✅ 3 | ✅ | ✅ | ❌ final /kʃ/ | ⚠ | ✅ | ❌ vowel onset |
| Vyoma | ⚠ 5 | ❌ 2 | ❌ **/ʋ/** | ✅ | ❌ /vj/ onset | ✅ | ❌ | ⚠ |
| **Solvani** | ✅ 7 | ✅ 3 | ❌ **/ʋ/** | ✅ | ⚠ /lv/ | ⚠ | ⚠ /s/ only | ✅ /s/ |
| Go | ❌ 2 | ❌ 1 | ✅ | ✅ | ✅ | n/a | ❌ | ✅ |

### 4.3 Why the deprecated incumbent scores poorly — evidence, not hindsight

**Solvani** fails two of the four Indian-English constraints. Its medial **/ʋ/ sits exactly on
the /v/~/w/ merger**, so the same speaker may produce *sol-vaa-ni* or *sol-waa-ni* on different
takes — variance injected into the positive class at no benefit.

This is not a retrospective rationalisation. The predecessor project's own hard-negative list
was **`sovani`, `solvaniya`, `silvany`, `sylvani`, `salwani`, `silvani`, `solvanee`, `so many`,
`sol vani`, `solvany`** — ten confusables, and it independently identified *so many* / *sol
vani* / *solvany* as the three hardest. **A keyword that generates a dense confusable
neighbourhood before you have even collected data is the wrong keyword**, and this one did.
"Sol" and "vani" are also separately meaningful fragments, which is what lets ordinary speech
reconstruct it.

---

## 5. Hard-negative analysis

Derived per FakeWake's finding that **false accepts concentrate on shared phonetic snippets,
not whole-word edit distance**. For each candidate the "decisive factors" are the stressed
syllable and the onset; hard negatives are constructed by perturbing those.

### 5.1 Takshila — predicted confusable set

| Class | Items | Why it is a risk |
|---|---|---|
| **Onset-sharing** | *taxi*, *taxable*, *tax law*, *tactical*, *taxonomy*, *tax filing* | share /tæks/ ≈ /t̪əkʃ/ — the decisive onset snippet |
| **Stressed-syllable sharing** | *she'll*, *sheila*, *sheela*, *shilaa*, *Sheila's*, *shielding* | share the stressed /ʃiː(l)/ nucleus |
| **Full-word near-neighbours** | *Taxila* (English pronunciation), *Takshashila*, *Takshak* | the intended word said differently |
| **Cross-lingual** | *raksha*, *shiksha*, *lakshya*, *daksha*, *paksha*, *moksha* | share the क्ष conjunct — very common in Indian speech |
| **Segmented** | "*tak* … *sheela*", "*talk* *she'll* *ah*" | the sliding window may see a fragment boundary |
| **Fragment/partial** | *taksh-*, *-shila*, *tak-shee* | **partial-word negatives** — the sliding-window failure mode |

The **क्ष family is the most important group** and is not obvious from English intuition:
*shiksha*, *raksha*, *lakshya* are frequent in Indian conversation and share the decisive
middle. They must be in **training**, not only in test.

### 5.2 Chetaki and Sanjika — why they rank lower

| Candidate | Confusable neighbourhood | Assessment |
|---|---|---|
| **Chetaki** | *Chetan*, *Chetana*, *Chetak* (Bajaj scooter, HAL helicopter), *Ketaki*, *chataki*, *check it*, *jetty* | **"Chetan" is a high-frequency Indian given name.** A wake word one phoneme from a common name is a standing false-alarm source in exactly the room where the demo happens. |
| **Sanjika** | *Sanjay*, *Sanjana*, *Sanjeev*, *Sangeeta*, *sanjeevani*, *sandwich*, *sanction* | **"San-" is one of the densest onsets in Indian given names.** Same objection, slightly weaker because the discriminative content sits in syllables 2–3. |

### 5.3 The rule this analysis produced

> **A keyword's false-alarm risk is dominated by the *density of its phonetic neighbourhood in
> the deployment language community*, not by its dictionary status.**

Two non-obvious consequences:

1. **Reject space-topical keywords.** *Antariksh* (space) and *Nakshatra* (star) score highest
   on ISRO resonance and are **disqualified by it**: they are exactly the words that will be
   spoken aloud at a space-themed demonstration, in front of the judges. A semantically apt
   keyword is a false-alarm liability *in proportion to its aptness*. Candidate 7 scores **1/5**
   on E for this reason.
2. **Reject common given names.** *Kalpana*, *Sanketa*, and to a lesser degree *Chetaki* and
   *Sanjika* sit inside dense name neighbourhoods. Someone calling a person across the room is
   an uncontrolled trigger source.

---

## 6. SIH / ISRO contextual analysis

**The honest finding first:** PS26172's own Background text is about **consumer voice-controlled
IoT**. No ISRO document ties it to a mission, and it names Raspberry Pi and ESP32 — neither
space-qualified. **Any "ISRO relevance" claim for a keyword is presentation, not requirement**,
and it is scored ×1 for that reason.

That said, the surrounding evidence is real and worth using:

| Evidence | Bearing on keyword choice |
|---|---|
| **PS26173 (iTantra)** — ISRO's adjacent PS — is *"Indian Multilingual TTS & STT … for low bitrate links"*, sharing verbatim boilerplate with PS26172 | The authoring group is explicitly interested in **Indian-language speech**. An Indian-rooted keyword is contextually congruent, not decorative. |
| **PS26174** states ISRO's edge rationale in its own words: restricted bandwidth to ground, process locally, **voice-based alerts to astronauts** | Supports the hybrid edge/cloud story the keyword sits inside. |
| ISRO's **Distress Alert Transmitter** — 20,000+ units, NavIC, messages in the user's **native language**, inclusive of non-literate users | Supports an Indian-language identity over a Latinate one (*Orbita* scores 4 on O but 2 on C). |

**Takshila** draws on Indian intellectual heritage — an ancient centre of learning — which reads
as considered rather than arbitrary to an Indian judging panel, **without being topical to
space** and therefore without importing the domain false-alarm risk that sinks *Antariksh*.
That combination is the specific reason it wins criterion O *and* criterion E, which no other
candidate manages.

---

## 7. ESP32-S3 / WakeNet suitability analysis

| Aspect | Assessment |
|---|---|
| **WakeNet models** | **Not usable.** They are pre-trained Espressif wake-word models; C11 requires training on a custom keyword. We use the ESP-SR *specification* as evidence only. |
| **Espressif's 3–6 symbol rule** | Takshila = 3 syllables. **Compliant.** |
| **Audio format** | ESP-SR specifies 16 kHz / 16-bit signed / mono / WAV — identical to our INMP441 I²S capture path. Adopt verbatim. |
| **Model input window** | 3 syllables ≈ 0.5–0.7 s of speech, fitting the **49 × 13 = 1.0 s** input with margin for positional jitter. No architecture change. |
| **Inference budget** | Unchanged from `ARCHITECTURE.md`: 49×13 int8 DS-CNN with ESP-NN measured **84.17 ms** `[prior-build]`, inside the 100 ms hop. Keyword choice does not move this. |
| **Microphone match** | The /ʃ/ places sustained energy at 3–8 kHz, the INMP441's cleanest band, while **64.6 % of its noise energy is below 100 Hz** `[prior-build]`. The 125 Hz mel floor already discards that noise. **Keyword and microphone are matched by design, not coincidence.** |
| **Onset/offset for latency** | /t̪/ onset gives a sharp attack; final /aː/ gives a clean, voiced offset, which is what the end-of-keyword timestamp (*t₀* for the SIH latency metric) is latched on. |

**All `[prior-build]` figures above are from a different project and must be re-verified here
before being quoted as results.**

---

## 8. Dataset feasibility analysis

### 8.1 The gap between the industrial bar and our reality

| | Espressif spec | Realistic for this project |
|---|---|---|
| Speakers | > 500, ≥100 children | **20–40**, adults |
| Entries | ≥ 20,000 | **~2,000–4,000** positive utterances |
| Environment | professional audio room < 40 dB | ordinary rooms, real noise |
| Distances | 1 m, 3 m | 0.3 / 1 / 2 / 3 m |
| Device | hi-fi microphone | **the actual INMP441** — *an advantage, see below* |

**We will be ~15× short on speakers.** Stating that plainly is more useful than a plan that
pretends otherwise. Three things partially close the gap:

1. **Keyword choice** — the free lever this entire document is about. More distinct phonetic
   elements ⇒ fewer fuzzy words ⇒ lower FA at the same data volume (FakeWake).
2. **Device-matched recording.** Espressif records on hi-fi microphones and must generalise to
   cheap MEMS parts. **We can record on the deployment microphone itself**, eliminating a
   domain gap they have to engineer around.
3. **Open-source negatives at scale** — thousands of speakers of *negative* data are free
   (§8.2). The asymmetry that killed the predecessor is on the *positive* side only.

### 8.2 External data sources — licence audit

| Source | Licence | Commercial use | Incorporable? | Purpose here |
|---|---|---|---|---|
| **LibriSpeech** | **CC BY 4.0** | ✅ yes | ✅ yes, with attribution | general unknown speech (negatives) |
| **Google Speech Commands** | **CC BY 4.0** | ✅ yes | ✅ yes, with attribution | short-command negatives |
| **MUSAN** | CC licences / US public domain; curated so **all content permits commercial use** | ✅ yes | ✅ yes | music, speech, noise backgrounds |
| **RIRS_NOISES (OpenSLR 28)** | **Apache 2.0** | ✅ yes | ✅ yes | room impulse responses for reverb augmentation |
| **Mozilla Common Voice** | **CC0** (public domain) | ✅ yes | ✅ yes, no attribution required | **accent-diverse negatives, incl. Indian English** |
| **ESC-50** | **CC BY-NC 3.0** | ❌ **non-commercial only** | ⚠ **acceptable for an academic competition entry; blocks any commercial future** | environmental noise |
| **Piper TTS** | **GPL-3.0** (`OHF-Voice/piper1-gpl`; the archived MIT `rhasspy/piper` was made read-only Oct 2025) | ⚠ engine is GPL | ⚠ **audio output is not a derivative work of the synthesiser, but voice models carry their own licences — check each** | synthetic hard negatives; synthetic positives only if A/B-gated |

**Two licensing actions follow.** First, **prefer Common Voice over ESC-50 wherever possible**
and record our own environmental noise: ESC-50's NC clause is the only genuine restriction in
the set, and the predecessor used it. Second, **if TTS is used, record the specific voice
model's licence per voice**, not just the engine's.

### 8.3 Feasibility verdict

**Feasible**, with the positive class as the schedule risk. Takshila is as collectable as any
other candidate — 3 syllables, unambiguous spelling-to-sound for Indian speakers, no
pronunciation coaching required (criterion S = 5/5 for all serious candidates; it does not
discriminate, and is scored honestly as such).

---

## 9. Recommended top 3

| Rank | Candidate | Score | Case for | Case against |
|---|---|---|---|---|
| **1** | **Takshila** /t̪əkˈʃiː.laː/ | **149** | 7 phonemes, 4 manner classes, 5 places; vowels span the space; /ʃ/ matched to the mic's clean band; क्ष is native to our speakers but rare in general English; heritage identity **without** space topicality | *taxi/tax-* onset family; the क्ष family (*shiksha*, *raksha*) is frequent in Indian speech; "Takshashila Institution" exists as an org name |
| **2** | **Hey Takshila** | 137 | Strictly lower FA than any single word | **Does not fit the 1.0 s window** — would force a larger input, and the prior build measured a 26.6× inference penalty for that. Retained only as the control that proves the window constraint is binding. |
| **3** | **Sanjika** /sənˈdʒiː.kaː/ | 134 | Excellent manner diversity (/s/, /dʒ/, /k/); clean phonotactics; fully invented ⇒ no trademark exposure | **"San-" is among the densest onsets in Indian given names** — an uncontrolled trigger source in the demo room |

*Chetaki* (129) and *Chatika* (132) are close behind; *Chatika* is the strongest choice if a
**purely invented** word is preferred over one with heritage meaning.

---

## 10. Final recommended keyword

# **Takshila**  /t̪əkˈʃiː.laː/ — "tuk-SHEE-laa"

3 syllables · 7 phonemes · CVC·CV·CV
**CONFIRMED and binding** — `DECISIONS.md` **D-011**.

---

## 11. Why it wins

1. **It clears every published structural threshold.** 7 phonemes (> Picovoice's 6-phoneme
   floor, > "Alexa"'s 6), 3 syllables (inside both Picovoice's 2–4 and Espressif's 3–6).
2. **It maximises distinct phonetic elements** — 4 manner classes, 5 places of articulation.
   This is the property FakeWake identifies as protective: detectors with *fewer* distinctive
   elements produced significantly more fuzzy words.
3. **It survives every Indian-English constraint.** No /v/~/w/, no dental fricative, no cluster
   requiring epenthesis, and three maximally separated vowels. Its one juncture, क्ष, is a
   **native conjunct for our speakers** while being rare in general English — an asymmetry that
   simultaneously lowers FRR for our users and FAR against English background speech.
4. **It is matched to this exact microphone.** The /ʃ/ puts sustained energy in the 3–8 kHz band
   the INMP441 resolves most cleanly, above the sub-100 Hz region holding 64.6 % of its noise
   energy `[prior-build]`.
5. **It fits the architecture unchanged** — ~0.6 s inside a 1.0 s window, no input resize, no
   inference-time penalty.
6. **It is evocative without being topical.** It earns the ISRO/Indian-heritage narrative that
   *Antariksh* and *Nakshatra* earn, but **without** their fatal property: it will not be spoken
   aloud during a space-themed demonstration.
7. **It is not a common given name**, which is the dominant uncontrolled trigger source in this
   deployment context and the reason *Chetaki*, *Sanjika*, *Kalpana* and *Sanketa* rank lower.
8. **It is directly comparable against the deprecated incumbent on the evidence**: *Solvani*
   violates the /v/~/w/ constraint and had already generated a ten-item confusable list before
   any data was collected.

---

## 12. Risks of the selected keyword

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| K-1 | **The /t̪əkʃ/ onset resembles *taxi*, *tax*, *tactical*, *taxonomy*.** English business speech contains "tax" often. | **High** | Put the whole *tax-* family in **training** hard negatives (§13). Measure FA/hour on speech containing them. |
| K-2 | **The क्ष family (*shiksha*, *raksha*, *lakshya*, *moksha*) is frequent in Indian conversation** and shares the decisive middle. | **High** | Same — these are the *most* important hard negatives and must be in train, not only test. |
| K-3 | **"Takshashila Institution" is a real Indian think tank**; *Taxila* is a UNESCO site. | Low–Med | No technical impact. Branding: we use the *Takshila* spelling and claim no affiliation. Verify no live trademark in the relevant class before any commercial use. |
| K-4 | Judges unfamiliar with the word may say **"Taxila"** (2 syllables) and fail to trigger. | Medium | Show the pronunciation on the dashboard; rehearse. Optionally accept *Taxila* as a second positive variant — **only if** measured to not raise FA. |
| K-5 | The unstressed initial /ə/ may reduce or drop in fast speech → *"kshila"*. | Medium | Explicit **fast-speech** recordings (§14); include reduced forms as positives, not negatives. |
| K-6 | English-speaking judges may epenthesise: *"tak-uh-shila"*. | Low | Include a small non-Indian-accent positive subset if speakers are available. |
| K-7 | **Selection is a prediction, not a measurement.** Every FA claim here is an argument from published phonetics, not a measured rate. | **High — stated deliberately** | The Phase-C streaming harness measures the truth. **If measured FA/hour is unacceptable, revisit this document, not the threshold.** |

---

## 13. Recommended hard negatives

Target **≥ 60 unique confusable phrases**, from many voices, with **the hardest in `train`**.
The predecessor's failure mode — 10 phrases with the 3 hardest held out of training — must not
recur.

### Tier 1 — decisive-snippet sharers (highest priority, must be in train)

| Group | Items |
|---|---|
| **क्ष family (Indian speech)** | shiksha · raksha · lakshya · moksha · daksha · paksha · rakshak · suraksha · pariksha · aksha · vriksha · diksha |
| **/tæks/ onset family** | taxi · tax · taxes · taxable · tax law · tax filing · taxonomy · tactical · taxidermy · tax-free · taximeter |
| **stressed /ʃiːl/ nucleus** | Sheila · sheela · she'll · shield · shielding · shilling · Shilpa · sheeling |

### Tier 2 — full-word near-neighbours

takshak · takshashila · taxila · takshaka · tak-shila (hyper-articulated) · thakshila · dakshila · lakshila · takshira · takshina

### Tier 3 — segmented and cross-boundary (the sliding-window failure mode)

"talk she'll ah" · "tak … sheela" · "attack shield" · "that's a shield" · "take a seat, Sheila" ·
"tax she left" · "stock she'll allow"

### Tier 4 — partial-keyword negatives (**structurally essential**)

Windows containing **≥ 50 % of the keyword outside the frame**: *taksh-* alone · *-shila* alone ·
*tak-shee-* · *-shee-laa*. The predecessor measured a deployed model firing on **49.7 %** of
realistic sliding windows against **10.7 %** on its curated clip set — a **4.6× optimism** caused
precisely by the absence of these `[prior-build]`. **These are not optional.**

### Tier 5 — general and background

Common Indian names sharing any onset (*Takshak*, *Tarun*, *Tanvi*) · ordinary conversational
speech · Common Voice Indian English · LibriSpeech · Speech Commands.

---

## 14. What data must be collected

Against the 14 required dimensions.

| # | Dimension | Specification |
|---|---|---|
| 1 | **Positive utterances** | **≥ 20 speakers** (target 30–40), ≥ 40 utterances each ⇒ 800–1,600 raw positives |
| 2 | **Hard-negative confusers** | ≥ 60 unique phrases (§13), multiple voices, **hardest in train** |
| 3 | **General unknown speech** | LibriSpeech + Common Voice (incl. Indian English) |
| 4 | **Background speech** | multi-talker babble, TV/radio, MUSAN speech |
| 5 | **Silence** | true digital silence **and** room tone recorded on the INMP441 |
| 6 | **Environmental noise** | fan, AC, traffic, keyboard, footsteps, door — **recorded ourselves** where ESC-50's NC clause is a concern |
| 7 | **Realistic acoustic conditions** | small room, large room, corridor, outdoor; + RIRS_NOISES (Apache 2.0) convolution |
| 8 | **Device-specific** | **all positives recorded through the actual INMP441 on the ESP32-S3**, 16 kHz / 16-bit / mono, matching ESP-SR's format |
| 9 | **Speaker diversity** | ≥ 20 speakers; balance gender; span L1 backgrounds (Hindi, Tamil, Malayalam, Bengali, Marathi, Telugu…); record age |
| 10 | **Distance** | **0.3 m, 1 m, 2 m, 3 m** (extends Espressif's 1 m/3 m) |
| 11 | **Orientation** | on-axis, 45°, 90°, behind |
| 12 | **Volume** | whisper, soft, normal, loud |
| 13 | **Speech rate** | slow, normal, fast (Espressif's 5/5/5 split per distance) |
| 14 | **Accent/pronunciation** | *Takshila*, *Taxila*, reduced *kshila*, hyper-articulated *tak-shi-la* |

**Non-negotiable process rules**

- **Keep every raw, uncut session.** The predecessor could not re-cut its positives because the
  raw sessions were lost. Store under `data/recordings`, never delete.
- **Record speaker ID with every file.** Splits must be **speaker-disjoint** — no speaker may
  appear in more than one split. This is the only way a speaker-independence claim becomes
  measurable, and it was impossible for the deprecated corpus.
- **Hold out a true evaluation set** — speakers reserved from the start, never used for tuning
  or threshold sweeps.
- **Design positional spread deliberately** — the keyword must appear at varied offsets within
  the window, including partial presentations.

---

## 15. Exact next-stage dataset specification

### 15.1 Splits — speaker-disjoint, fixed before collection

| Split | Speakers | Purpose |
|---|---|---|
| `train` | ~65 % | model fitting |
| `validation` | ~20 % | early stopping, architecture choice |
| `test` (**held out**) | ~15 %, **≥ 5 speakers** | touched **once**, at the end |

Plus two **stream sets** for the Phase-C harness: **SWEEP** (choose the operating point) and
**VALIDATE** (disjoint, never used for tuning).

### 15.2 Directory layout

```
data/
├── recordings/                      # RAW, never deleted, never edited
│   └── <speaker_id>/<session_id>/*.wav + session.json
└── dataset/                         # built, reproducible from recordings/
    ├── manifests/{train,validation,test}.csv
    └── {train,validation,test}/{positive,hard_negative,unknown,background,silence}/
```

`session.json` records speaker id, L1, gender, age band, room, distance, orientation, volume,
rate, device, and consent status.

### 15.3 Audio format — fixed

16 kHz · 16-bit signed · mono · WAV · 1.000 s clips (16,000 frames), matching both ESP-SR's
specification and the 49×13 model input.

### 15.4 Class scheme

`positive` · `hard_negative` · `unknown` (general speech) · `background` (noise/music) ·
`silence`. Five classes, not three — the predecessor's 3-class scheme conflated hard negatives
with general unknowns and could not measure the distinction that matters.

### 15.5 Evaluation protocol — written now, before collection

| Metric | Definition | Role |
|---|---|---|
| **FRR at fixed FA/h** | false rejection rate at **0.5 and 1.0 false alarms/hour** on negative-only audio | **headline** |
| **FA/hour** | false activations per hour of keyword-free audio | **headline** |
| **DET curve** | FRR vs FA across thresholds | operating-point selection |
| **Detections per spoken keyword** | streaming, sliding-window, real smoothing rule | **headline** |
| Precision / recall / F1 | clip level | **secondary diagnostic, always labelled** |
| **Detection latency** | keyword end → decision → first packet → ASR receipt | SIH-graded |
| Robustness breakdown | per speaker, distance, volume, rate, noise condition | reporting |

FRR-at-fixed-FA/h and DET curves are the standard KWS operating-point conventions; common
operating points are 0.5, 1 and 10 FA/h.

**Rules:** sweep on SWEEP, validate on VALIDATE. A number swept and judged on the same audio is
**provisional**. No clip-level figure is ever reported as a detector figure. Never report "100 %
accuracy" — report FRR at a stated FA/h.

### 15.6 Immediate next actions

1. ~~Confirm the keyword~~ — **DONE**, recorded as binding decision **D-011**.
2. **Write the recording protocol** (Phase 0.3): prompts, session structure, consent form,
   accept/reject quality bar, and the `session.json` schema in §15.2.
3. **Run ONE pilot session** and measure it with `tools/audio_probe.py` and
   `tools/audio_probe_bands.py` **before recruiting any speaker.** A format, level or
   centring fault found in a pilot costs one session; found after recruitment it costs all of
   them.

---

## Sources

- [Picovoice — Tips for Choosing a Wake Word](https://picovoice.ai/docs/tips/choosing-a-wake-word/)
- [Picovoice — Wake Word Detection Guide 2026](https://picovoice.ai/blog/complete-guide-to-wake-word/)
- [Espressif ESP-SR — Speech Wake-up Solution Customization (ESP32-S3)](https://docs.espressif.com/projects/esp-sr/en/latest/esp32s3/wake_word_engine/ESP_Wake_Words_Customization.html)
- [Espressif ESP-SR — WakeNet Wake Word Model](https://docs.espressif.com/projects/esp-sr/en/latest/esp32s3/wake_word_engine/README.html)
- [FakeWake: Understanding and Mitigating Fake Wake-up Words of Voice Assistants (arXiv 2109.09958)](https://arxiv.org/html/2109.09958)
- [Schönherr et al., Unacceptable, where is my privacy? Exploring Accidental Triggers of Smart Speakers (arXiv 2008.00508)](https://arxiv.org/pdf/2008.00508)
- [US9275637B1 — Wake word evaluation (Amazon)](https://patents.google.com/patent/US9275637B1/en)
- [Sensory — Custom Wake Words: Branded Voice UX Guide 2026](https://sensory.com/custom-wake-words-branded-voice-ux-guide-2026/)
- [Oxford English Dictionary — Indian English pronunciation](https://www.oed.com/information/understanding-entries/pronunciation/world-englishes/indian-english/)
- [Phonetic Peculiarities of the English Language in India (IJSCL)](https://www.ijscl.com/article_241951_a15237d176e59f6236b49c3389015f63.pdf)
- [MUSAN: A Music, Speech, and Noise Corpus (arXiv 1510.08484)](https://arxiv.org/pdf/1510.08484)
- [Speech Commands: A Dataset for Limited-Vocabulary Speech Recognition (arXiv 1804.03209)](https://arxiv.org/pdf/1804.03209)
- [OpenSLR 28 — Room Impulse Response and Noise Database](https://www.openslr.org/28/)
- [Mozilla Common Voice](https://en.wikipedia.org/wiki/Common_Voice)
- [Piper TTS — licensing overview](https://www.cekura.ai/discover/piper-tts)
- [Efficient keyword spotting using dilated convolutions and gating (arXiv 1811.07684)](https://arxiv.org/pdf/1811.07684)
