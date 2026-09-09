# DECISIONS.md

Decisions that are expensive or impossible to reverse later, each with its reasoning and its
consequences. Architecture-level deviations from the supplied documents are numbered `A-n` in
`ARCHITECTURE.md` section 8; those are cross-referenced here rather than repeated.

---

## D-001 — Project root is `E:\sih2026`, not the Desktop folder

**Date:** 2026-09-09 · **Status:** active · **Decided by:** Claude (environment-forced)

**Decision.** The build tree lives on `E:\sih2026`. The Desktop folders keep the original
source material (PDFs, zips) and the prior build.

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
- The project is **one self-contained root on one drive**: `E:\sih2026`. Dataset, source,
  artifacts, build output and the venv all live inside it. Nothing is split across drives.
- PlatformIO **core** stays at `C:\Users\Menon\.platformio` (2.4 GB of compiler toolchains).
  This is a *tool installation*, in the same category as `git.exe` and `python.exe` — not
  project data. Only `build_dir` points into `E:\sih2026\.pio`.
- The Python venv and `PIP_CACHE_DIR` go on E:.
- `D:\sih-ml-env` (TensorFlow 2.21.0, from the prior build) is deliberately **not** adopted —
  using it would split the project across drives. `D:\speech_commands` (5.37 GB) may be read as
  an external corpus, the same way any system-installed dataset would be.
- E: is a **HDD, not SSD** — feature extraction over 21k small files will be I/O-bound.
  Cache features to a single `.npz` rather than re-reading WAVs each epoch.
- Fully reversible: if C: later gains ~27 GB, the tree can be moved wholesale.

---

## D-002 — Keyword is `solvani`

**Date:** 2026-09-09 · **Status:** locked by the supplied data

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

## D-004 — The positive class is the project's binding constraint; plan around it explicitly

**Date:** 2026-09-09 · **Status:** active

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

**Decision.** Generate `solvani` from many open-source TTS voices to attack the one-speaker
ceiling, and also expand the phonetic hard negatives the same way (the shipped set has only
**10** unique confusable phrases, and the three hardest — `so many`, `sol vani`, `solvany` —
appear only in validation/test, never in train).

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
