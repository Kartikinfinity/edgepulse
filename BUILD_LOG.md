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
