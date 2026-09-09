# DECISIONS.md

Decisions that are expensive or impossible to reverse later, each with its reasoning and its
consequences. Architecture-level deviations from the supplied documents are numbered `A-n` in
`ARCHITECTURE.md` section 8; those are cross-referenced here rather than repeated.

---

## D-001 — The project is one self-contained tree, on a volume with room for it

**Date:** 2026-09-09 · **Status:** active · **Amended 2026-09-09 (D-009): the root is now
machine-independent** · **Decided by:** Claude (environment-forced)

**Decision.** The project is **one self-contained root**: source, docs, dataset, artifacts,
build output and the virtual environment all live under a single directory, on a volume with
enough free space. It is never split across drives.

> **The root is not a fixed path.** On the original machine it was `E:\sih2026`; every
> absolute path below is the historical record of *why* that machine needed a non-default
> location. Since D-009 the repository resolves its root at runtime via `config/paths.py` and
> can be cloned anywhere on Windows or Linux.

**Why.** Measured on this host: C: is a 128 GB NVMe that was **100 % full (0 bytes free)**.
D: and E: are partitions of a 1 TB SATA HDD with 337 GB and 446 GB free. A Phase-1 build needs
a 570 MB dataset expanded to 21,267 WAVs, feature caches, model checkpoints, PlatformIO build
output and an ASR model download — none of which fitted. The Desktop folder is also inside
**OneDrive**, so large binary artefacts would be continuously sync-churned.

**Re-tested 2026-09-09 after a safe cleanup — decision reaffirmed.** A cache-only cleanup
recovered **12.36 GB**, taking C: to **12.84 GB free (10.85 %)**. The decision was then
re-evaluated against measured requirements rather than assumed ones:

| Quantity | Value |
|---|---:|
| C: free after cleanup | 12.84 GB |
| Project total (measured + projected) | ≈ 12 GB |
| Windows headroom needed on a 118 GB system volume | ≈ 15 GB |
| **Required** | **≈ 27 GB** |
| **Shortfall** | **≈ 14 GB** |

Migrating would leave C: at roughly **0.8 GB free** — exactly the failure state the cleanup was
performed to escape. Closing the 14 GB gap would require uninstalling software or deleting
personal data, both of which are out of bounds. Full working: `STORAGE_AUDIT.md` §12.

**Consequences.**
- The project is **one self-contained root on one volume**. Dataset, source, artifacts, build
  output and the venv all live inside it. Nothing is split across drives.
- The PlatformIO **core** directory (~2.4 GB of compiler toolchains) stays wherever PlatformIO
  installs it, outside the repository. This is a *tool installation*, in the same category as
  `git` and `python` — not project data. Firmware build output goes to `<root>/firmware/.pio`,
  which is the PlatformIO default and needs no configuration.
- The Python venv lives at `<root>/.venv`. On a volume that is short of space, redirect
  `PIP_CACHE_DIR` rather than moving the venv out of the tree.
- `D:\sih-ml-env` (TensorFlow 2.21.0, from the prior build) is deliberately **not** adopted —
  using it would split the project across drives. `D:\speech_commands` (5.37 GB) may be read as
  an external corpus, the same way any system-installed dataset would be.
- The original volume was a **HDD, not an SSD** — feature extraction over many small files is
  I/O-bound there. The general rule stands on any machine: **cache features to a single `.npz`
  rather than re-reading every WAV each epoch.**
- Superseded by **D-009**: the tree is no longer tied to any volume and can be cloned anywhere.

---

## D-002 — ~~Keyword is `solvani`~~ **VOID (superseded by D-010, 2026-09-09)**

> **THIS DECISION NO LONGER HOLDS.** The dataset that locked the keyword was deprecated and
> removed from the project. **Keyword selection is reopened and is now the project's first
> task** — see `DATASET.md` §5. Nothing below may be used to argue for any particular keyword.
> The *selection criteria* it applied (syllable count, band placement, rarity, crisp onset)
> remain a reasonable starting checklist; the conclusion does not.

**Date:** 2026-09-09 · **Status:** ~~locked by the supplied data~~ **VOID**

**Decision.** The keyword is **`solvani`**. Not a free choice — the supplied dataset is built
for it, and it is the only keyword for which positive audio exists.

**Assessment against the criteria the prior build used.** 3 syllables (~0.55 s measured active
span, `DATASET.md` section 6), sibilant `/s/` onset placing energy in the 4–8 kHz band where
the INMP441's measured noise floor is lowest `[prior-build]`, not a common English word, and
a crisp onset that helps end-of-keyword timestamping for the latency metric. It is a good
keyword on the same grounds the prior one was chosen.

**Consequence.** Changing it invalidates the entire dataset. It will not be changed.

---

## D-003 — Stay on Arduino core 2.0.17 / ESP-IDF 4.4 for Phase 1

**Date:** 2026-09-09 · **Status:** active · Cross-ref `ARCHITECTURE.md` A-5

**Decision.** Build on the installed PlatformIO stack (`espressif32 @ 7.1.1`,
`framework-arduinoespressif32 3.20017` = Arduino core 2.0.17, ESP-IDF 4.4) with an
Arduino-compatible TFLM port and ESP-NN enabled. Do **not** migrate to ESP-IDF 5.x now.

**Why.**
- The supplied implementation plan asks for ESP-IDF 5.x + `driver/i2s_std.h` +
  `espressif/esp-tflite-micro`. That is the better long-term stack.
- But it is **the only stack in this project with measured on-hardware evidence**: 84.17 ms
  inference, 15,460 B arena, MFCC parity at 1.0000000000 correlation `[prior-build]`. The
  claimed advantage of IDF 5.x — ESP-NN SIMD kernels — was already obtained here by setting
  `-DESP_NN=1 -DCONFIG_IDF_TARGET_ESP32S3=1`, worth a measured **5.48x** `[prior-build]`.
- A toolchain migration costs a multi-GB download (C: has 0 bytes free, D-001) and hours of
  integration, against a 12–16 h budget where the binding constraint is *data*, not runtime.

**Consequence.** Legacy `driver/i2s.h` is used. Migration to ESP-IDF 5.x is a Phase-2 item,
to be revisited if and only if a measured limitation demands it.

---

## D-004 — ~~The positive class is the binding constraint~~ **VOID as a data claim (D-010); the lesson is retained**

> **The specific numbers below are OUT OF SCOPE** — they describe the deprecated corpus.
> **What survives is the design principle**, now recorded as a requirement in `DATASET.md` §2:
> a positive class drawn from one speaker cannot be repaired by augmentation, threshold
> tuning, or more public negative speech — each was demonstrated exhausted on hardware.
> **Therefore speaker diversity in the positive class is the primary design variable for the
> new dataset**, to be planned in from the start rather than discovered afterwards.

**Date:** 2026-09-09 · **Status:** ~~active~~ **VOID as a statement about this project's data**

**Decision.** Treat the 110-utterance / one-speaker positive class as **the** engineering
problem, and allocate Phase D to it before any architecture search.

**Evidence.** Measured here: positives are 790 clips from **110 unique recordings**, 100 %
`speaker_01`, 2 environments; the test split holds **17** unique positive utterances
(`DATASET.md` section 3). Measured in the prior build on hardware: negative-data expansion
and decision-logic tuning were each independently exhausted, and hard-negative mining showed
Speech Commands contributing only 0.14 % of false positives — i.e. more public negative
speech does not help `[prior-build]`.

**Consequences.**
- No result from this dataset may be described as **speaker-independent**.
- Threshold tuning is explicitly *not* a way out; it moves along the frontier only.
- The demo must state its speaker-dependence honestly, or Phase D must change it (D3/D6).

---

## D-005 — Headline accuracy comes from a streaming simulation, never from clip accuracy

**Date:** 2026-09-09 · **Status:** active · Cross-ref `ARCHITECTURE.md` A-6

**Decision.** The reported detection rate and false-activation rate are produced by sliding
the real inference window over continuous audio with the real smoothing rule
(`BUILD_PLAN.md` Phase C). Clip-level accuracy is a secondary diagnostic, always labelled as such.

**Why — this is the most transferable lesson available to this project.** The prior build made
the same mistake twice and it invalidated every accuracy figure it had:
1. A deployed model whose curated test set reported 10.7 % false-fire was measured firing on
   **49.7 %** of realistic sliding windows — the evaluation was wrong before the model was.
2. After that was fixed, held-out windows still came from the same narrow recording sessions
   as training, leaving the false rate optimistic by roughly **12x** against natural speech.
3. A near-miss: one model would have been reported as a success (false fires 11.88 to
   0.00/min) until fresh validation measured **0/10 detection** — it had "solved" false
   positives by never saying "keyword". `[prior-build]`

**Consequences.** The evaluation harness is built **before** the model. Operating points are
swept on a SWEEP stream set and then validated on a disjoint VALIDATE set. A number swept and
judged on the same audio is reported as *provisional* and nothing else.

---

## D-006 — ASR runs on the LAN host, and the transport is raw PCM over WebSocket

**Date:** 2026-09-09 · **Status:** active · Cross-ref `ARCHITECTURE.md` A-1, A-4

**Decision.** The "cloud" is a server process on the host PC (192.168.1.2), reached over
Wi-Fi. ASR is **faster-whisper** (MIT / CTranslate2), int8 on CPU. Audio is streamed as raw
PCM16 in binary WebSocket frames, with the connection held open while LISTENING.

**Why.** The problem statement requires a *remote ASR server* and forbids proprietary or
commercial voice SDKs. A LAN server is remote from the MCU, is fully open-source, removes
internet dependence from a live demo, and lets us measure the "keyword end to ASR receipt"
latency precisely with a clock-offset handshake. Opus encoding was rejected: it adds latency,
CPU and a failure mode to buy bandwidth that is free on a LAN and is not a graded metric.
Holding the socket open removes the TCP/WS handshake from the critical path.

**Consequence.** Needs Wi-Fi credentials (open blocker). A `SERVER_URI` setting still permits
a genuinely remote endpoint if desired.

---

## D-007 — Synthetic (TTS) positives are gated by an A/B, not adopted on faith

**Date:** 2026-09-09 · **Status:** proposed · Cross-ref `ARCHITECTURE.md` A-7

**Decision.** If the new dataset still ends up positive-class-limited, generate the selected
keyword from many open-source TTS voices to attack the speaker ceiling, and build the phonetic
hard-negative set the same way — with the hardest confusables placed in **train**, not only in
validation/test.

> **Note (D-010):** collecting real speakers is strictly better than synthesising them. This
> decision is a fallback, and the new dataset should be designed so it is not needed.

**Guard.** Synthetic positives ship **only if** a model trained with them beats one trained
without them, judged on **real** held-out positives through the Phase-C streaming harness.
Synthetic speech differs from real speech in ways that may not transfer; the A/B is the test.

**Rule check.** The problem statement forbids models *pre-trained on generic smart-assistant
keywords*. Using an open-source TTS system to synthesise audio for our own custom keyword is
data augmentation, not a pre-trained keyword model, and no proprietary voice-activation SDK
is involved.

---

## D-008 — VAD is an indicator by default, not a gate on KWS

**Date:** 2026-09-09 · **Status:** active · Cross-ref `ARCHITECTURE.md` A-2

**Decision.** VAD is implemented and displayed, and it drives end-of-utterance detection, but
it does not gate the KWS path unless `VAD_GATES_KWS` is set.

**Why.** Measured on this dataset: speech-band (300–3400 Hz) energy fraction is 0.561 for
positives versus **0.538 for background** (`DATASET.md` section 6) — an energy VAD separates
almost nothing here, because the backgrounds include music and broadband noise and the
positives were recorded in fan and classroom noise. Gating on it would drop real keywords to
buy CPU that Phase 1 has been told to ignore.

**Consequence.** Idle CPU stays high in Phase 1 (prior build: 48 % of one core). That is a
declared, displayed Phase-2 debt, not an oversight.

---

## D-009 — The repository is machine-independent; paths resolve at runtime

**Date:** 2026-09-09 · **Status:** active · Amends **D-001**

**Decision.** No tracked source file may contain an absolute path, a drive letter, a username,
or a machine-specific tool location. Everything resolves through `config/paths.py`, which
derives the project root from its own file location and layers in optional overrides.

Resolution order for every setting: **real environment variable → `<root>/.env` → built-in
default relative to the root.**

**Why.** The project must continue on a second computer, Windows or Linux, without losing any
knowledge or state. Hard-coded paths are the single most common reason a handoff fails, and
this repository had three of them (`ROOT = r"E:\sih2026\data\..."` in each `tools/` script)
plus a documentation set that told the reader to `cd E:/sih2026`.

**Consequences.**
- `config/paths.py` is the only place that knows how to find anything. It imports **standard
  library only**, so it works before any dependency is installed.
- `.env` is git-ignored; `.env.example` is committed and contains **no values**, only keys and
  explanation. Wi-Fi credentials and any other secret live only in `.env`.
- `firmware/platformio.ini` pins no `upload_port`. Port names differ per machine (COM7 on the
  original Windows host, `/dev/ttyACM0` on Linux); PlatformIO auto-detects, and
  `SIH_UPLOAD_PORT` overrides.
- The dataset stays out of Git. `dataset_manifest/` — a JSON summary plus 21,285 SHA-256
  digests — lets a second machine prove byte-identical data without the 0.64 GB of WAVs.
- **Historical records are exempt and must not be rewritten.** `STORAGE_AUDIT.md`, the
  `[prior-build]` rows in `HARDWARE.md`, and the evidence sections of `BUILD_LOG.md` and D-001
  document what was true on one machine on one date. Editing those paths out would falsify a
  measurement record. The rule applies to *code and instructions*, not to history.

**Verification.** `scripts/verify_setup.py` (machine readiness), `scripts/verify_dataset.py`
(data integrity against the committed manifest), `scripts/health_check.py` (project state).
The `tools/` scripts were re-run from an unrelated working directory to confirm they no longer
depend on the caller's location.

---

## D-010 — The supplied dataset is deprecated; the project restarts dataset-first

**Date:** 2026-09-09 · **Status:** active · **Decided by:** the user (change of project
direction) · Supersedes **D-002**, voids the data claim in **D-004**

**Decision.** The previously supplied corpus is removed from the project. It may not be used
for training, validation, testing, benchmarking, architecture decisions, preprocessing
decisions, dataset statistics, augmentation design, keyword selection, conclusions,
documentation, or future recommendations. **The project now has no approved dataset and no
selected keyword**, and the first task is keyword selection followed by designing and building
a dataset from first principles.

**Why.** A direction change by the user. No technical defect in the corpus forced it; this
decision records the instruction and its consequences rather than arguing for it.

**Scope of the reset — what was actually removed.**
- Tracked files whose only purpose was that corpus: `dataset_manifest/` (manifest + 21,285
  checksums), `DATASET_SETUP.md`, `scripts/verify_dataset.py`,
  `scripts/generate_dataset_manifest.py`, `tools/analyze_manifests.py`. All recoverable from
  history at `2c4500c`.
- Every active reference in shared documentation and configuration.
- The 674 MB on disk was **quarantined, not deleted** — disposing of the user's data is the
  user's call.

**What was deliberately retained, and why.**
- **All hardware knowledge** (ESP32-S3-WROOM-1-N16R8 GPIO constraints, PSRAM/flash facts,
  INMP441 electrical and I²S detail) — independent of any dataset.
- **The architecture** and its eight deviations — the pipeline shape does not depend on which
  corpus feeds it.
- **D-005**, the evaluation methodology: streaming metrics over continuous audio, never clip
  accuracy; SWEEP/VALIDATE separation; host/device feature parity. This is dataset-independent
  and is the most valuable lesson the project holds.
- **The design lesson from the deprecated corpus' failure**, restated as a *requirement* in
  `DATASET.md` §2: speaker diversity in the positive class is the primary design variable, raw
  recordings must be kept, positional spread must be deliberate, and splits must be
  speaker-disjoint. The numbers are out of scope; the engineering principle is not.
- Two dataset-agnostic measurement tools, rewritten to take a directory argument.

**Consequences.**
- No metric of any kind may currently be quoted for this project. `EXPERIMENT_STATE.md` is
  reset accordingly.
- Keyword selection reopens with no incumbent. The old keyword carries no weight.
- The dataset must be **versioned and fingerprinted** once built; a fingerprint mechanism will
  be reintroduced when its structure is known. Audio never enters Git.
- **No Git history rewrite was performed and none is required** — no dataset binary was ever
  committed. Analysis in `GIT_HISTORY_DATASET_PURGE.md`.

---

## D-011 — Custom wake keyword: **`Takshila`** — CONFIRMED

**Date:** 2026-09-09 · **Status:** **ACTIVE — confirmed by the user** · **Decided by:** the user,
on the research in `KEYWORD_SELECTION.md` · Supersedes the void D-002

**Decision.** The custom wake keyword is **`Takshila`**, /t̪əkˈʃiː.laː/ ("tuk-SHEE-laa") —
3 syllables, 7 phonemes, structure CVC·CV·CV.

**This is now binding.** The dataset, the hard-negative set, the recording prompts and the
product identity are all built on it. Changing it later invalidates every recording made.

**Why, in one paragraph.** It clears every published structural threshold (7 phonemes against
Picovoice's 6-phoneme floor; 3 syllables inside both Picovoice's 2–4 and Espressif's 3–6), and
it maximises *distinct* phonetic elements — 4 manner classes across 5 places of articulation —
which is the property FakeWake identifies as protective, having shown that detectors relying on
fewer distinctive elements produce significantly more fuzzy words. It satisfies all four Indian
English constraints that eliminate most candidates: no /v/~/w/ contrast, no dental fricative, no
cluster requiring epenthesis, and three maximally separated vowels (/ə/–/iː/–/aː/). Its one
juncture, क्ष, is a **native conjunct for Indian speakers but rare in general English** — an
asymmetry that lowers FRR for our users and FAR against English background speech at the same
time. Its /ʃ/ places sustained energy in the 3–8 kHz band the INMP441 resolves most cleanly,
above the sub-100 Hz region carrying 64.6 % of its noise energy `[prior-build]`. At ~0.6 s it
fits the existing 1.0 s / 49×13 input with no architecture change.

**Two rejections that carry general lessons.**
- **Space-topical keywords are disqualified by their aptness.** `Antariksh` and `Nakshatra`
  score highest on ISRO resonance and worst on false activation, because they are exactly the
  words spoken aloud at a space-themed demonstration, in front of the judges.
- **Common given names are disqualified.** In the Indian deployment context, someone calling a
  person across the room is an uncontrolled trigger source. This is what ranks `Chetaki`
  (*Chetan*), `Sanjika` (*Sanjay/Sanjana*), `Kalpana` and `Sanketa` below the recommendation.

**Consequences.**
- One word, not two: a carrier phrase would exceed the 1.0 s window and force a larger input,
  which the prior build measured at a **26.6×** inference penalty `[prior-build]`.
- The hard-negative set is defined by the **क्ष family** (*shiksha*, *raksha*, *lakshya*) and the
  **/tæks/ family** (*taxi*, *tax*, *tactical*) — both must be in **training**, not only test.
- Positive recordings must cover the reduced fast-speech form *kshila* and the mispronunciation
  *Taxila*.

**Known risk, stated plainly.** Every false-alarm claim in the research is a **prediction from
published phonetics, not a measurement**. The Phase-C streaming harness measures the truth. If
the measured FA/hour is unacceptable, the correct response is to **revisit the keyword**, not to
tune the threshold — `DECISIONS.md` D-005 and the predecessor's experience are unambiguous that
decision-logic tuning does not create detection capability.

---

## D-012 — KWS engine: custom neural model on TFLite Micro + ESP-NN

**Date:** 2026-09-09 · **Status:** active · Full comparison: `KWS_ENGINE_DECISION.md`
Cross-ref D-003 (toolchain), D-005 (evaluation), D-011 (keyword)

**Decision.** The inference engine is a **custom neural KWS model trained by us and deployed
through TensorFlow Lite for Microcontrollers with ESP-NN kernels**, on the installed Arduino
core 2.0.17 / ESP-IDF 4.4 stack. **ESP-SR / WakeNet is rejected. microWakeWord is rejected as a
runtime but adopted as a data strategy, and is the declared fallback.**

**Why ESP-SR / WakeNet is eliminated — availability, not preference.** Custom WakeNet training
is **not self-service**. Espressif offers a paid corpus-collection-and-training service (and
third parties resell the same), with a **2–3 week turnaround** and a **>500-speaker,
≥100-children, ≥20,000-entry** corpus prerequisite. It cannot begin today, let alone finish
inside a 12–16 h window. It is also an ESP-IDF component against our Arduino stack.

**Why microWakeWord is rejected as a runtime, despite being good.** It is Apache 2.0,
self-service, streaming (MixConv, after Rybakov et al., arXiv 2005.06720), int8, TFLM-based, and
it explicitly optimises **false accepts per hour** — our headline metric. But it is built for
ESPHome/ESP-IDF, and its `micro_speech` frontend applies **noise suppression and AGC**.
Reproducing that frontend bit-exactly on our stack is a host/device parity problem, and D-003
already records that an IDF-5.x migration costs a multi-GB download and hours we do not have.
**The risk would land in the final hours before the demo — the worst place to put it.**

**Why B wins.** It is the only option with **measured evidence on this exact board and
toolchain**: 84.17 ms/inference, 15,460 B arena, ESP-NN worth **5.48×**, and MFCC host/device
parity at correlation 1.0000000000 `[prior-build]`. Everything else is projection. It also makes
PS compliance unambiguous — C10 (open-source TinyML) and C11 (trained on a custom keyword) are
satisfied by construction, and the licences are clean (TFLM and the `ESP_TF` Arduino port are
both Apache 2.0).

**Adopted from microWakeWord anyway.** Its **synthetic-first data strategy**: Piper TTS
generation is the proven way to get breadth without speakers, which is exactly tomorrow's
constraint. Used **without reservation for hard negatives** (we need the model to reject a phone
sequence, and a synthetic *shiksha* contains क्ष genuinely) and **only under the D-007 A/B gate
for positives**. Synthetic speech is never presented as equivalent to diverse real speakers.

**Pre-declared fallback.** If the training pipeline has not produced a converging model by
**T+6 h**, switch to microWakeWord and accept the frontend-port risk. A working model on a
different runtime beats no model. This trigger is declared now so it is not a judgement made
under pressure later.

**Consequences.**
- The feature pipeline is **ours to define** — TFLM imposes none. The 49×13 / 25 ms / 20 ms
  pipeline stands, verified rather than assumed (`KWS_ENGINE_DECISION.md` §4).
- **Inference cadence is 200 ms, not one per 20 ms hop.** At 84.17 ms/inference, one inference
  per hop would need 421 % CPU. 200 ms gives ~42 % duty and matches the only cadence with a
  measured figure on this board.
- A **known limitation is accepted for Tier 1**: utterances slower than ~880 ms cannot satisfy
  the positive-class margin rule inside a 1.0 s window. The slow rate is prompted as
  "deliberate, not drawn out" and over-length takes are flagged and excluded rather than
  silently mislabelled. Widening to 1.2 s (60×13) is the first Tier-2 architecture experiment.

---

## D-013 — Two-tier dataset strategy; the demo is not blocked on research-grade data

**Date:** 2026-09-09 · **Status:** active · **Decided by:** the user (project-management change)

**Decision.** The dataset is split into two explicit tiers. **Tier 1
(`DEMO_DATASET_SPEC.md`)** — 6 speakers, ~3.5 h of data work — is built now and is what the
demo runs on. **Tier 2 (`RESEARCH_DATASET_ROADMAP.md`)** — 30 speakers, 20 h of continuous
audio, ~70–85 h — is preserved unchanged as a post-demo target and **does not block this build**.

**What is reduced, and what explicitly is not.** Only **scale** is reduced. Every
methodological control carries across unchanged: speaker-disjoint splits, the ten enumerated
leakage assertions, the metadata schema, the hard-negative tier strategy, partial-keyword
negatives, offset-sampling-is-not-augmentation, recorded-not-mixed test conditions, the QC
thresholds, and the continuous-audio evaluation protocol. **A small dataset built correctly is
defensible; a large one built carelessly is not.**

**The honesty obligation this creates.** With 6 speakers the system is
**speaker-dependent-leaning**, and the test split holds ~40 positives — a **±9.5 pp** confidence
interval. With 3–6 h of continuous audio, an FA/hour figure is an **order-of-magnitude**
statement, not a number: at a true 0.5 FA/h, 3 h gives a 95 % CI of 0.10–1.83 FA/h.
**No speaker-independence claim may be made**, and every reported rate must carry its CI and
observation duration. `RESEARCH_DATASET_ROADMAP.md` is the documented answer to "what would you
do with more time".
