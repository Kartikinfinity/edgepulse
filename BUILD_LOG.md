# BUILD_LOG.md

Append-only. One entry per experiment or build step. **Every entry declares its pass/fail bar
before the result**, so a result cannot be judged against a bar invented after seeing it.

Template:

```
## EXP-NNN — <title>
Date · Phase · Status: PASS | FAIL | PARTIAL | INCONCLUSIVE

**Objective.**
**Hypothesis.**
**Pre-declared pass bar.**   <- written before running
**Method.**
**Measurements.**
**Analysis.**
**What this does NOT prove.**
**Next.**
```

---

## EXP-000 — Discovery and project bootstrap
**Date:** 2026-09-09 · **Phase:** discovery · **Status:** PASS
**⚠ ALL DATASET FINDINGS BELOW ARE VOID — see OPS-003 / `DECISIONS.md` D-010.**

> The corpus these measurements describe was **deprecated and removed from the project**.
> The clip counts, split counts, leakage results, speaker distribution, keyword-position and
> band-energy figures below are **out of scope** and may not be quoted for any purpose —
> not as a result, not as a baseline, not as background.
>
> This entry is retained **unedited** because it is a dated measurement record and editing it
> would falsify the log. The *host and toolchain* facts in it remain valid.

**Objective.** Establish, from the supplied files and the actual machine, what is
authoritative, what is proposed, and what genuinely blocks implementation — before writing
any implementation code.

**Pre-declared pass bar.** Every supplied document read; the complete dataset inspected
structurally *and* acoustically; the hardware and toolchain identified by measurement rather
than assumption; blockers named; persistent project documentation created.

**Method.** Extracted and read all 5 PDFs; enumerated both working trees and the prior build's
19-experiment log; extracted the 570 MB dataset archive and its 42,628-entry nested archive;
analysed all 21,267 manifest rows with `tools/analyze_manifests.py`; probed audio format and
keyword position with `tools/audio_probe.py` and `tools/audio_probe_bands.py`; queried the
host for drives, serial devices, GPU, network and installed toolchain versions.

**Measurements.**

*Dataset (the full set of findings is in `DATASET.md`)*
- 21,267 WAVs across two prebuilt variants; 17,183 (full) + 4,084 (balanced) manifest rows;
  **0 files missing**.
- Format uniform on a 1,500-file random sample: mono / 16,000 Hz / 16-bit PCM / exactly
  16,000 frames. No exceptions.
- **Positives: 790 clips from 110 unique recordings, 100 % `speaker_01`, 2 environments**
  (`fan` 60, `classroom` 50). Train/val/test unique positives = 77 / 16 / **17**.
- Leakage: **0 of 2,387** `source_id` values, and 0 of 2,387 `original_source` values, appear
  in more than one split. Recording-disjoint. Not speaker-disjoint (impossible: one speaker).
- Phonetic hard negatives: **10 unique TTS phrases**; the three hardest (`so many`,
  `sol vani`, `solvany`) are in validation/test only, never in train.
- Keyword position within the 1.0 s window (300–3400 Hz band, 110 unaugmented positives):
  active span ~545 ms, mean lead 235 ms / trail 221 ms, peak-bin std 5.1 bins (±255 ms).
- Speech-band energy fraction: positive 0.561, negative 0.662, **background 0.538**.
- 4 of 110 unaugmented positives contain a full-scale sample (mild clipping).

*Host*
- C: 128 GB NVMe, **0 bytes free**; D: 337 GB free, E: 446 GB free (both on one 1 TB SATA HDD).
- i3-8100 4C/4T, 15.9 GB RAM, Intel UHD 630 — **no CUDA**.
- Ethernet up, 192.168.1.2/24, internet reachable. Wi-Fi adapter present, **disconnected**.
- **No `VID_303A` device enumerated** — the ESP32 is not attached.
- PlatformIO 6.1.19 · `espressif32@7.1.1` · `framework-arduinoespressif32 3.20017`
  (Arduino core 2.0.17) · **ESP_IDF_VERSION 4.4** · xtensa-esp32s3 toolchain present.
- Python 3.13.9 → TensorFlow 2.20.0, torch 2.8.0+cpu. Python 3.14.0 → numpy/scipy/sklearn/matplotlib.

**Analysis.** The supplied dataset is well built — uniform format, honest recording-disjoint
splits, sensible augmentation, and its own leakage check is genuine. Its one weakness is
decisive: the positive class is 110 utterances from a single speaker, which is the exact
constraint that ended the prior build. That makes Phase D, not architecture search, the
highest-value work. Separately, the environment has a hard obstacle — a completely full C:
drive — that forces the project onto E:.

**What this does NOT prove.**
- Nothing about this hardware has been measured **in this tree**; every `[prior-build]` figure
  in `HARDWARE.md` is unverified here.
- No model, feature pipeline, or firmware exists yet, so no accuracy, latency, CPU or memory
  claim can be made at all.
- The wiring is unconfirmed pending the authoritative pin map.
- The dataset was assessed structurally and acoustically, not by listening to the clips.

**Next.** `BUILD_PLAN.md` A1–A2 (venv on E:, PlatformIO skeleton), then Phase B (feature
pipeline) and Phase C (streaming evaluation harness) — none of which needs the board.

---

## Housekeeping performed in EXP-000

- Deleted `C:\c\...\solvani_kws_release.zip` (560,988,160 B) — an artefact this session created
  when a POSIX path (`/e/...`) was passed to `C:\Python314\python`, which resolved it to
  `C:\e\...` on the full C: drive. Recovered 509 MB. **No user file was touched.**
  The trap is recorded in `CLAUDE.md` section 1.

---

## OPS-001 — Safe storage recovery and storage-strategy decision
**Date:** 2026-09-09 · **Phase:** environment (SIH implementation halted by the user for this
task) · **Status:** PASS

**Objective.** Recover usable space on C: without touching anything personal or system-owned;
decide whether the project can live on C: as one self-contained tree; locate the raw
`Desktop\data` recording tree; verify the final filesystem and toolchain state.

**Pre-declared pass bar.** (1) C: free space materially increased using only regenerable
caches; (2) zero user documents, applications, Windows components, browser profiles, Recycle
Bin contents, pagefile or restore configuration modified; (3) every tool still functional
afterwards; (4) a storage decision justified by measured numbers, with the project on exactly
one drive; (5) the raw-data question answered definitively.

**Method.** Full audit first, no deletions (`STORAGE_AUDIT.md` §§1–9). Each cleanup target was
identity-checked before removal — e.g. `npm config get cache` was run to confirm the npm cache
path, and `Arduino15\staging\packages` was listed to confirm all 36 entries were extractable
archives whose extracted form still exists in `Arduino15\packages`. Deletions used explicit
paths only; no wildcard spanned a parent directory. pip and uv were cleared with their own
documented commands where available.

**Measurements.**

| | bytes | GB |
|---|---:|---:|
| C: free before | 519,274,496 | 0.48 |
| C: free after | 13,791,440,896 | **12.84** |
| **Recovered** | **13,272,166,400** | **12.36** |

By category: npm `_cacache`+`_logs` ~5.3 GB · pip cache 3.93 GB (pip reported 3,503 files) ·
Arduino staging 2.03 GB (36 files) · PlatformIO `.cache` 0.68 GB · uv cache 0.37 GB · two named
stale Temp staging dirs ~0.30 GB.

Raw-data search across **all three fixed drives**, four independent methods: no directory named
`data` under any Desktop, no directory whose name contains `solvani` outside the release, no
directory matching the manifest's raw session names, no `noise_00*.wav` file. **The tree does
not exist on this machine.**

Storage decision arithmetic: project ≈ 12 GB + Windows headroom ≈ 15 GB = **≈ 27 GB required**
against **12.84 GB available** ⇒ **~14 GB short** ⇒ project stays on `E:\sih2026`.

**Post-state verification.** git 2.51.2 · Python 3.14.0 / 3.13.9 · pip 26.0.1 · npm 11.6.1 ·
node v24.11.0 · PlatformIO Core 6.1.19 with `espressif32` and all 9 packages intact ·
TensorFlow 2.20.0 + torch 2.8.0+cpu · `D:\sih-ml-env` TensorFlow 2.21.0 · `tools/analyze_manifests.py`
reproduces its documented output · dataset 21,267 WAVs with all 18 per-split class counts
matching `DATASET.md` §2 · `git fsck` clean, working tree clean, 13 tracked files.

**Analysis.** The cleanup was worth 12.36 GB from caches alone, which both removes the acute
0-bytes-free hazard and leaves every installed tool working. It does **not** change the storage
decision: C: would still be left at under 1 GB after hosting the project, and the only paths to
another 14 GB run through installed software or personal data. E: at 445.79 GB free is ~35× the
project's projected lifetime footprint.

**What this does NOT prove.**
- Shadow-copy / System Restore usage on C: is **unmeasured** — `vssadmin` requires elevation.
  There may be further reclaimable space there; changing it is out of scope by instruction.
- No claim is made that C: is now "healthy"; 10.85 % free on a system volume is workable, not
  comfortable, and it will refill as caches regenerate.
- Nothing about the SIH build itself was advanced. No model, firmware, or feature code exists.

**Next.** Await the user's explicit instruction before resuming the SIH build. When resumed,
the first unblocked step is unchanged: `BUILD_PLAN.md` A1–A2, then Phases B and C.

---

## OPS-002 — Cross-machine portability and handoff preparation
**Date:** 2026-09-09 · **Phase:** environment (SIH implementation still halted by the user)
**Status:** PASS

**Objective.** Make the repository completely portable and reproducible on a second Windows or
Linux machine, without losing project knowledge, decisions, experiments, architecture, dataset
understanding or development state. The Git repository — not any chat transcript — becomes the
sole source of truth.

**Pre-declared pass bar.** (1) No tracked *code or instruction* contains an absolute path,
drive letter or username; (2) every analysis script runs unchanged from an unrelated working
directory; (3) a second machine can prove it holds byte-identical data without the WAVs being
in Git; (4) setup, verification and health-check scripts exist and run; (5) no secret is
committed; (6) the working tree is clean and committed.

**Method.**
- Audited the tree and enumerated every hardcoded-path hit, then classified each as *project
  configuration* (must fix) or *historical record* (must NOT be rewritten).
- Added `config/paths.py`: derives the project root from its own file location, layers
  environment variable → `.env` → relative default. Standard library only, so it works before
  any dependency is installed.
- Repointed the three `tools/` scripts at it and re-ran them from an unrelated cwd.
- Generated a committed dataset fingerprint and wrote a verifier for it.
- Added dependency files, portable `firmware/platformio.ini`, setup scripts for both OSes, and
  three verification scripts.
- Hardened `.gitignore` and tested it in both directions.

**Measurements.**

| Item | Result |
|---|---|
| Hardcoded paths in tracked **code** before → after | **3 → 0** (`tools/*.py`) |
| Hardcoded paths in **instructional docs** before → after | 16 → 0 (`CLAUDE.md`, `DATASET.md`, D-001) |
| Hardcoded paths left in **historical records** | 32, deliberately preserved — see below |
| `tools/analyze_manifests.py` run from an unrelated cwd | ✅ identical output |
| Dataset fingerprint | 21,285 files · 685,589,976 B · root SHA-256 `34a1a266…d243de90` |
| `CHECKSUMS.sha256` | 2.67 MB, one digest per file, sorted, POSIX relative paths |
| `scripts/verify_dataset.py` | PASS (layout, counts, 6 manifest-CSV digests, 200 sampled files) |
| `scripts/verify_setup.py` | correctly reported NOT READY under Python 3.14 (no TensorFlow wheels) — the failure path works |
| `.gitignore` | 8 must-track paths tracked, 10 must-ignore paths ignored |
| Secrets committed | **none** — `.env.example` contains keys and comments, no values |

**Analysis.** The three `ROOT = r"E:\sih2026\..."` constants were the only true portability
defects in code; the rest of the exposure was instructional text telling a reader to `cd` into
a specific drive. Both are now gone. The dataset was the harder problem: it must not enter Git
at 0.64 GB, yet a second machine needs certainty it has the right bytes. A per-file SHA-256
list plus a single root hash costs 2.67 MB in the repository and answers that exactly, and it
also localises a fault to the individual clip rather than merely reporting a mismatch.

Absolute paths were **deliberately left** in `STORAGE_AUDIT.md`, the `[prior-build]` rows of
`HARDWARE.md`, and the evidence sections of `BUILD_LOG.md` and D-001. Those document what was
measured on one machine on one date; editing the paths out would falsify a measurement record.
The portability rule governs code and instructions, not history.

**What this does NOT prove.**
- **The handoff has not been rehearsed on a second machine.** Nothing here was executed on a
  clean Windows or Linux host; `setup.ps1`/`setup.sh` are untested end to end, and
  `requirements.txt` has not been resolved from scratch on a fresh interpreter.
- `firmware/platformio.ini` has **never been built** — there is no `src/`, so `pio run` cannot
  succeed yet. Its pins and flags are carried from the prior build and are unverified here.
- The dataset fingerprint proves *identity*, not *correctness*. It confirms two machines hold
  the same bytes; it says nothing about whether the labels are right.
- No SIH implementation was started. No model, no firmware, no server, no UI.

**Next.** Await explicit authorisation to push, then to begin `BUILD_PLAN.md` A1 → A2 → B → C.

---

## OPS-003 — Dataset reset and active-context purge
**Date:** 2026-09-09 · **Phase:** direction change (SIH implementation still not started)
**Status:** PASS

**Objective.** Remove the previously supplied KWS corpus from the ACTIVE project — not merely
ignore it — so that it cannot influence training, validation, testing, benchmarking,
architecture, preprocessing, statistics, augmentation design, keyword selection, conclusions,
documentation or recommendations. Restate the project as dataset-first.

**Pre-declared pass bar.** (1) Every tracked file whose sole purpose was that corpus is gone
from the active tree; (2) no active code or configuration resolves to it; (3) no active
document treats it as the dataset; (4) no stale artifact can become the new baseline; (5)
general SIH, hardware, architecture and methodology knowledge is preserved; (6) any Git history
question is analysed and reported, with **no destructive rewrite performed**; (7) a re-scan
finds no surviving active reference.

**Method.** Full inventory first, no modifications — `DATASET_RESET_AUDIT.md`. Each reference
was classified as *project configuration* (fix), *reusable capability* (rewrite), or
*historical record* (leave, because editing it would falsify a dated measurement).

**Measurements.**

| Item | Result |
|---|---|
| Tracked files before → after | 35 → 31 |
| Files removed (old-dataset-only) | 6 — `dataset_manifest/` ×2, `DATASET_SETUP.md`, `verify_dataset.py`, `generate_dataset_manifest.py`, `analyze_manifests.py` |
| Files rewritten to be dataset-agnostic | 2 — `tools/audio_probe.py`, `tools/audio_probe_bands.py` |
| Shared docs/config updated | 14 |
| **Dataset binaries ever committed** | **none** — verified across all refs |
| Largest blob in entire history | `CHECKSUMS.sha256`, 2.67 MB of **text** |
| `.git` size | 1.4 MB |
| Git LFS involvement | **none** — no filters, no LFS files |
| Model / checkpoint / feature artifacts | **none existed anywhere** — Phase 3 was a null case |
| Training or evaluation logs | none |
| On-disk corpus | 674 MB **quarantined, not deleted** |
| Remote | none configured; nothing was ever published |

**Analysis.** The reset was unusually clean because the corpus never entered Git — it lived
only in the git-ignored `data/` directory. That makes a history rewrite unnecessary, which is
the finding that matters most: a rewrite would have invalidated every commit hash the
documentation cites, to reclaim 2.6 MB of text from a 1.4 MB repository. Analysis and the
exact procedure, should it ever be ordered, are in `GIT_HISTORY_DATASET_PURGE.md`. **No
history was rewritten.**

Two decisions were voided in place rather than deleted: **D-002** (keyword) and the data claim
in **D-004** (positive-class constraint). Deleting them would have destroyed the reasoning
trail. D-004's *lesson* — that a single-speaker positive class cannot be repaired by
augmentation, threshold tuning or more public negatives — was promoted from a finding about
one corpus into a **design requirement** on the next one (`DATASET.md` §2). That is the single
most valuable thing carried across the reset.

**What this does NOT prove.**
- **Nothing about the new dataset**, which does not exist. No keyword is selected, no criteria
  are defined, no recording has been made.
- The rewritten probes are syntactically valid and were exercised, but **have not been run
  against a real new-dataset directory**, because none exists.
- The 674 MB on disk is quarantined, not deleted — the project cannot resolve to it, but the
  bytes are still there until the user disposes of them.
- No claim is made that the deprecated corpus was defective. It was removed by instruction.

**Next.** Keyword selection (blocker **B-5**), then the dataset design specification
(**B-6**) — `DATASET.md` §5. Hardware bring-up remains independent and unblocked apart from
the pin map.

---

## EXP-001 — Custom wake keyword selection (research)
**Date:** 2026-09-09 · **Phase:** dataset-first Phase 0.1 · **Status:** **PASS — `Takshila`
CONFIRMED by the user 2026-09-09 and recorded as binding decision D-011**

**Objective.** Determine, scientifically rather than aesthetically, the optimal custom wake
keyword for this product, and specify the dataset that must follow from it. Nothing trained,
nothing collected.

**Pre-declared pass bar.** (1) Current official Espressif ESP-SR documentation and current
credible KWS research consulted on the web, not from memory; (2) ≥10 candidates evaluated
against all 20 requested criteria with a transparent, weighted rubric that a deliberately bad
control fails; (3) phonetic analysis grounded in the *speaker population's* phonology, not
generic English; (4) hard negatives derived by a method the literature supports; (5) every
external data source licence-checked with commercial-use status; (6) all 15 required outputs
produced; (7) no keyword selected without the research behind it.

**Method.** Read the official requirement audit for PS26172 and the ISRO context reconstruction
from the project's own research base. Fetched Espressif's ESP-SR wake-word customization
specification and Picovoice's wake-word selection guidance directly. Searched and read current
research: FakeWake (arXiv 2109.09958), Schönherr et al. accidental triggers (arXiv 2008.00508),
Amazon's wake-word evaluation patent US9275637B1, Sensory's 2026 custom wake word guide, and
KWS evaluation-metric conventions. Compiled Indian English phonological constraints from OED
and IJSCL. Licence-audited seven external corpora and one TTS engine.

**Measurements / findings.**

| Finding | Source |
|---|---|
| ≥6 phonemes required; "Alexa" = 6, "OK Google" = 8; 2–4 syllables; phonetic variety over length | Picovoice |
| Espressif's production bar: **>500 speakers, ≥100 children, ≥20,000 entries**, <40 dB room, 1 m + 3 m × 15 reps | ESP-SR docs |
| False accepts concentrate on **phonetic snippets, not whole-word similarity**; **Levenshtein distance fails** to separate fuzzy from non-fuzzy; sparse-feature detectors produce more fuzzy words; 130 fuzzy words for Echo Dot, 322 for AliGenie; >40 % survive volume/speed/noise change | FakeWake |
| An Echo Dot reliably fired on **89 words**, some phonetically distant from "Alexa" | Schönherr et al. |
| Wake-word candidates should be scored by **how often their phone sequence occurs in general speech** | US9275637B1 |
| Indian English: **/v/~/w/ merge**, dental fricatives → stops, reduced vowel inventory, cluster simplification | OED, IJSCL |
| Licences: LibriSpeech CC BY 4.0 · Speech Commands CC BY 4.0 · MUSAN CC/public-domain, commercial-safe · OpenSLR-28 RIRs Apache 2.0 · Common Voice **CC0** · **ESC-50 CC BY-NC 3.0 (non-commercial only)** · Piper TTS moved MIT → **GPL-3.0** | vendor/dataset sources |

18 candidates scored on a weighted 20-criterion rubric. Result: **Takshila 149**, Hey Takshila
137, Sanjika 134, Chatika 132, Shalaka 130, Chetaki 129 … Solvani (deprecated incumbent) **95**,
and the deliberately-bad control "Go" **58** — a 2.5× separation confirming the rubric
discriminates.

**Analysis.** Three findings did real work. **First**, the industrial bar is ~500 speakers and we
will manage 20–40, so robustness must be bought through keyword choice — the one free lever —
and FakeWake says the currency is *distinct phonetic elements*, not length. **Second**, Indian
English phonology *eliminates* candidates rather than merely ranking them, and it retired the
deprecated incumbent on evidence: `Solvani`'s medial /ʋ/ sits exactly on the /v/~/w/ merger, and
the predecessor had already generated a ten-item confusable list for it before collecting data.
**Third**, and least obvious: **a semantically apt keyword is a false-alarm liability in
proportion to its aptness.** `Antariksh` and `Nakshatra` score highest on ISRO resonance and are
disqualified by it, because they are the words that will be spoken aloud at a space-themed
demonstration. The same logic retires common given names, which is the dominant uncontrolled
trigger source in this deployment context.

The one-word-versus-phrase question was settled on **our own architecture** rather than generic
advice: a carrier phrase runs ~1.0–1.2 s and does not fit the fixed 49×13 = 1.0 s input, and the
prior build measured a **26.6×** inference penalty for enlarging that input `[prior-build]`.

**What this does NOT prove.**
- **No false-alarm rate here has been measured.** Every FA claim is a prediction from published
  phonetics. The Phase-C streaming harness is what will falsify or confirm it.
- No audio has been recorded, no speaker recruited, no model trained.
- The `[prior-build]` microphone and inference figures used in the argument remain unverified in
  this tree.
- The rubric's weights are a defensible judgement, not an objective truth; a different weighting
  could promote Sanjika or Chatika. The top group is close and the argument, not the arithmetic,
  is what should be scrutinised.

**Outcome.** The user confirmed **`Takshila`** on 2026-09-09. **D-011 is now binding**, and the
keyword is propagated through `CLAUDE.md`, `DATASET.md`, `STATUS.md` (B-5 resolved),
`PROJECT_STATE.md`, `CURRENT_HANDOFF.md`, `EXPERIMENT_STATE.md` and `README.md`.

**Next — EXP-002.** Write the recording protocol (prompts, session structure, consent, the
accept/reject quality bar, the `session.json` schema) and run **one pilot session**, measured
with `tools/audio_probe.py` and `tools/audio_probe_bands.py`, **before recruiting any speaker.**
The data specification is already fixed in `KEYWORD_SELECTION.md` §§13–15 and is an input, not
something to redesign.

---

## EXP-002 — Dataset design specification
**Date:** 2026-09-09 · **Phase:** dataset-first Phase 0.2 · **Status:** PASS (design frozen;
**nothing collected, nothing trained**)

**Objective.** Produce a complete, buildable specification for a production-quality custom KWS
dataset for `Takshila` on the ESP32-S3 + INMP441, designed for continuous always-listening
operation, before any audio is recorded.

**Pre-declared pass bar.** (1) All 37 required sections present and specific enough to build
from; (2) the dataset supports both utterance-level and continuous-stream metrics — FRR, FA/h,
precision, recall, F1, DET, latency, and robustness by speaker/environment/distance/noise;
(3) leakage controls enumerated as testable assertions, not intentions; (4) test set never
augmented, never speaker-shared, never used for threshold tuning; (5) a long-form continuous
protocol capable of exposing false activations over hours; (6) every external source licence-
checked; (7) sizes given as both target and honest minimum.

**Method.** Derived every technical parameter from the fixed feature pipeline in
`ARCHITECTURE.md` §3 rather than choosing freely, and every phonetic decision from
`KEYWORD_SELECTION.md`. Cross-checked class design against the two predecessor failure modes
recorded in D-005.

**Key design decisions and their evidence.**

| Decision | Why |
|---|---|
| **Clip = exactly 1.000 s (16,000 samples)** | derived: 49 frames × 20 ms hop + 25 ms window = 985 ms, rounded |
| **Offset sampling is NOT augmentation** — applied to train, val AND test | it is the distribution the device sees; treating it as augmentation is what produced the predecessor's 4.6× optimism |
| **Windows holding 25–99 % of the keyword are `hard_negative/partial`** | the single most important rule; their absence caused a deployed model to fire on 49.7 % of realistic windows vs 10.7 % on its clip set `[prior-build]` |
| **6-way `class` label, 3-way `model_target`** | lets FA against near-homophones specifically be reported without retraining |
| **Test noise and reverb are RECORDED, not mixed** | otherwise the test measures our RIR/noise set, not the world |
| **`Takshashila` (V9) is a NEGATIVE, not a positive variant** | it is a different word; admitting it widens the boundary for no gain |
| **EV-2: 3 training speakers re-recorded ≥2 weeks later** | the only justified same-speaker crossing, and it exists because held-out windows from the same sessions left a predecessor's false rate optimistic by ~12× `[prior-build]` |
| **CS-INDIC: 4 h of Indic speech** | क्ष occurs naturally in Indian languages — keyword-specific FA exposure no other candidate would have needed |
| **Children excluded** | consent and ethics cannot be properly discharged here; the resulting gap is declared, not hidden |
| **ESC-50 avoided** | CC BY-NC 3.0 is the only genuine restriction in the source set; own recordings replace it |

**Sizes.** Target **30 speakers × 48 positives = 1,440 raw**, ~39,800 clips, ~15 GB with raw
sessions, plus **20 h** CS-VALIDATE / 8 h CS-WILD / 4 h CS-INDIC / 1 h CS-DETECT. Minimum
viable **15 speakers**, **≥120 held-out test positives**, **10 h** continuous audio.

**Statistical honesty, computed before measuring.** Test-positive count drives the CI:
120 → ±5.4 pp, 240 → ±3.8 pp, against the deprecated corpus's 17 → ±20 pp. And for false
alarms, at a true 0.5 FA/h: 10 h gives a 95 % CI of **0.16–1.17 FA/h**, 20 h gives
**0.24–0.92**, 40 h gives 0.31–0.77. **10 h resolves an order of magnitude, not a number.**
Every FA/h figure this project reports must carry its CI and its observation duration.

**Analysis.** Two things drove the design more than anything else. First, the predecessor's
failure was an *evaluation* failure twice over, so the spec spends its complexity on partial
negatives, offset sampling, recorded-not-mixed test conditions, and ten enumerated leakage
assertions that fail the build. Second, the one advantage this project has over the industrial
bar — Espressif needs 500 speakers and must generalise from hi-fi mics to cheap MEMS parts —
is that **we can record on the deployment microphone itself**. That advantage is only real if
the INMP441 is wired, which makes **B-1 the critical path for the entire project**, not merely
for firmware.

**What this does NOT prove.**
- **No audio has been recorded.** Every number here is a target, not a measurement.
- The 21-minute session estimate and the ≤10 % reject target are **predictions**; the pilot
  (EXP-003) is what tests them.
- The fractional-factorial condition design is a judgement about what is collectable in 21
  minutes, not an optimal experimental design.
- Speaker recruitment feasibility (30 speakers, ≥6 L1 backgrounds) is assumed, not secured.
- Nothing here validates the keyword. `Takshila`'s false-alarm behaviour remains unmeasured.

**Next — EXP-003.** Resolve **B-1**, wire the INMP441, complete A4/A5 bring-up, build
`firmware/recorder/` and `tools/record_session.py`, then run **ONE pilot session**. Exit bar:
format uniform, RMS in range, zero dropouts, visible keyword-onset spread, ≤10 % rejects.
**Do not recruit before the pilot passes.**

---

## EXP-003 — KWS engine selection, pipeline verification, keyword lock, dataset re-tiering
**Date:** 2026-09-09 · **Phase:** demo build, T-0 · **Status:** PASS (decisions recorded;
**nothing trained, nothing collected**)

**Objective.** Before collecting data, determine the actual inference engine; verify rather than
assume the feature/inference pipeline; sanity-check the keyword against the chosen engine; and
re-tier the dataset so the 12–16 h demo is not blocked on a research-grade corpus.

**Pre-declared pass bar.** (1) Three engine options evaluated against all 13 requested criteria
using current official documentation, not memory; (2) the winner justified on feasibility within
the window, not familiarity; (3) every pipeline parameter documented with its source and its
*derivation*, including inference cadence; (4) keyword either locked or stopped-on with a
reason; (5) a Tier-1 spec that is buildable in the remaining time with every methodological
control retained; (6) Tier 2 preserved and explicitly non-blocking.

**Method.** Fetched Espressif's ESP-SR customization documentation and searched for a
self-service path; fetched microWakeWord's repository, ESPHome component docs and licence;
identified the underlying architecture paper (Rybakov et al., *Streaming keyword spotting on
mobile devices*, arXiv 2005.06720). Scored all three against the requested criteria.

**Findings.**

| Finding | Consequence |
|---|---|
| **ESP-SR/WakeNet custom training is not self-service** — paid Espressif service or paid third party; **2–3 weeks**; prerequisite corpus **>500 speakers, ≥100 children, ≥20,000 entries** | **Eliminated on availability**, not preference. Cannot start today. |
| **microWakeWord is Apache 2.0, self-service, TFLM-based, streaming MixConv, int8, arena ~22,860 B, and explicitly optimises false-accepts-per-hour** | Genuinely strong; **rejected as a runtime** only because its `micro_speech` frontend applies **NS + AGC** and is ESPHome/ESP-IDF-shaped — a parity port landing in the final hours |
| **TFLM + ESP-NN is the only option with measured evidence on this board and toolchain** — 84.17 ms, 15,460 B arena, ESP-NN 5.48×, MFCC parity 1.0000000000 `[prior-build]` | **Selected (D-012)** |
| **TFLM imposes no feature pipeline** — it runs whatever graph it is given | The 49×13 / 25 ms / 20 ms pipeline is **ours**, which is exactly why it needed verifying. microWakeWord's very different 30 ms / 10 ms / 40-feature choice proves the point. |
| **Inference cadence ≠ hop.** At 84.17 ms, one inference per 20 ms hop needs **421 % CPU** | **200 ms cadence chosen** (~42 % duty; prior measured 48 % at this cadence). 100 ms available as a demo-day latency improvement. |
| **⚠ The 1.0 s window cannot hold a slow utterance.** Slow rate is 700–1000 ms; the ≥60 ms margin rule caps admissible duration at **880 ms** | Left unfixed, slow speech would be labelled `hard_negative/partial` — **training the model to reject deliberate speech**. Tier-1 fix: prompt slow as "deliberate, not drawn out", flag `duration_over_window`. Tier-2 fix: widen to 1.2 s (60×13). |

**Keyword sanity check — `Takshila` LOCKED.** Trainable on the chosen engine with no vocabulary
constraint; fits the window at normal and fast rates; /ʃ/ sits in the INMP441's cleanest 3–8 kHz
band; discriminative events survive 13-MFCC compression; ~600 ms spans ≥3 inference windows at
200 ms cadence, which is what makes M-of-N smoothing viable. **No serious technical reason to
change it was found.**

**Re-tiering (D-013).** Tier 1 = `DEMO_DATASET_SPEC.md`, **6 speakers × 40 positives**, ~3.5 h of
data work, minimum 3 speakers. Tier 2 = `RESEARCH_DATASET_ROADMAP.md`, unchanged, explicitly
non-blocking. **Only scale was reduced** — speaker-disjoint splits, the ten leakage assertions,
the metadata schema, partial-keyword negatives, offset-sampling-is-not-augmentation,
recorded-not-mixed test conditions and the QC thresholds all carry across intact.

**Analysis.** The engine decision was closer than expected. microWakeWord scored 53 to TFLM's 59
and is arguably the better *engineering* choice in a normal schedule — it is free, self-service,
streaming, and it optimises the exact metric the PS grades. It lost on one thing: **where its
risk lands.** Its frontend port would be debugged in the last hours before a demo, and D-003
already priced an IDF-5.x migration as unaffordable. Choosing the option with measured numbers
on this exact board is the correct trade under a deadline — and the fallback trigger at T+6 h is
declared now precisely so that judgement is not remade under pressure.

The most useful output was not the engine choice but the **cadence and window findings**. Both
were assumptions inherited from the architecture document; one turned out to be a 421 % CPU
impossibility if taken literally, and the other would have quietly trained the model to reject
slow speech. Neither was visible without doing the arithmetic.

**What this does NOT prove.**
- **No model has been trained and no audio recorded.** Every figure remains `[prior-build]` or a
  projection.
- microWakeWord was **not benchmarked on our hardware** — its rejection is a risk judgement
  about integration cost, not a measured performance comparison.
- The 200 ms cadence rests on a prior-build inference time that is **unverified in this tree**.
  If A4/A5 measure materially different timing, the cadence must be recomputed.
- The 880 ms window limit is derived from *expected* keyword durations; real durations are
  measured in the pilot.

**Next.** Resolve **B-1 (pin map)** — now the critical path for the entire build — wire the
INMP441, verify the bit shift (QC-8), then **record the test speaker first and quarantine it**.
Start CS-WILD ambient capture and Piper hard-negative generation immediately; both run unattended.
