# DATASET_RESET_AUDIT.md

Audit performed **before** any modification, as the record justifying the reset of the
deprecated `solvani_kws_release` dataset out of the active project.

**Date:** 2026-09-09 · **Repo HEAD at audit time:** `2c4500c` · **Working tree:** clean ·
**Remotes:** none configured (nothing has ever been pushed)

---

## 1. Headline finding

> **No dataset binary was ever committed to Git.** The largest object in the entire
> repository history is `dataset_manifest/CHECKSUMS.sha256` at 2.67 MB — a text fingerprint,
> not audio. The whole `.git` directory is **1.4 MB**.

This makes the reset unusually clean: there is **no large-blob history purge to perform**, and
because no remote exists, nothing was ever published. Details in
`GIT_HISTORY_DATASET_PURGE.md`.

## 2. Git and LFS state

| Check | Result |
|---|---|
| Git LFS installed | yes (3.7.1) |
| LFS filters in `.gitattributes` | **none** |
| Files tracked by LFS | **none** |
| Dataset binaries (`*.wav/.npz/.tflite/.keras/.h5/.pb/.zip`) in any commit | **none** |
| `.git` total size | 1.4 MB |
| Largest history blob | `dataset_manifest/CHECKSUMS.sha256`, 2,668,642 B |

## 3. On-disk material (untracked)

| Path | Contents | Size | Git status |
|---|---|---|---|
| `data/solvani_kws_release/` | 21,285 files (**21,267 WAV**) | **674 MB** | git-ignored, never committed |
| `artifacts/` | **empty** | 0 | git-ignored |
| `docs/experiments/` | **empty** | 0 | tracked dir, no content |

## 4. Model / feature / checkpoint artifacts

**NONE EXIST.** A repository-wide search for `*.npz *.npy *.tflite *.keras *.h5 *.ckpt *.pb
kws_model.* kws_params.h` returned nothing. No training log, no evaluation output, no
TensorBoard event file.

**Phase 3 of the reset is therefore a null case** — there is no stale artifact that could
accidentally become the new baseline, because nothing was ever trained in this repository.
This is stated as a fact, not as completed work.

## 5. Tracked files referencing the old dataset

35 files tracked; 21 carry at least one reference.

### 5a. Files whose ONLY purpose is the old dataset → to be removed

| File | Size | Why it cannot survive the reset |
|---|---:|---|
| `dataset_manifest/CHECKSUMS.sha256` | 2.67 MB | 21,285 SHA-256 digests of the deprecated audio |
| `dataset_manifest/manifest.json` | 3.3 KB | counts, splits and root hash of the deprecated dataset |
| `DATASET_SETUP.md` | 6.4 KB | how to obtain and verify the deprecated dataset |
| `scripts/verify_dataset.py` | 6.6 KB | verifies against the deprecated manifest |
| `scripts/generate_dataset_manifest.py` | 5.6 KB | generates that manifest |
| `tools/analyze_manifests.py` | 2.3 KB | parses the deprecated manifest CSV schema |

### 5b. Files with reusable value → to be generalised, not deleted

| File | Reusable part | Old-dataset coupling to remove |
|---|---|---|
| `tools/audio_probe.py` | WAV format audit, RMS/clipping/envelope statistics | hardcoded to `DATASET_FULL` and the release's split/class layout |
| `tools/audio_probe_bands.py` | band-limited (300–3400 Hz) keyword-localisation analysis | same |

These implement measurement techniques the **new** dataset will need immediately. Deleting
them would mean rewriting them. They are being rewritten to take a directory argument and
make no assumption about dataset layout.

### 5c. Shared files needing obsolete assumptions replaced

`CLAUDE.md` · `DATASET.md` · `STATUS.md` · `BUILD_PLAN.md` · `ARCHITECTURE.md` ·
`DECISIONS.md` · `BUILD_LOG.md` · `CURRENT_HANDOFF.md` · `PROJECT_STATE.md` ·
`EXPERIMENT_STATE.md` · `README.md` · `config/paths.py` · `.env.example` ·
`scripts/verify_setup.py` · `scripts/health_check.py` · `pyproject.toml`

### 5d. Historical records — retained unedited

`STORAGE_AUDIT.md` and the existing dated entries in `BUILD_LOG.md` record what was measured
on a specific machine on a specific date. Editing them would falsify a measurement record.
They are annotated as historical, not rewritten. New entries are appended.

## 6. Decisions invalidated by this change of direction

| ID | Decision | Status after reset |
|---|---|---|
| **D-002** | "Keyword is `solvani`, locked by the supplied data" | **VOID** — the data that locked it is deprecated. Keyword selection reopens. |
| **D-004** | "The positive class (110 utterances, one speaker) is the binding constraint" | **VOID as a statement about this project's data.** The *lesson* — a small single-speaker positive class cannot be fixed by augmentation or threshold tuning — is retained as a design principle for building the new dataset. |
| D-005 | Streaming metrics, never clip accuracy | **RETAINED** — dataset-independent methodology, and the most valuable lesson available. |
| D-001, D-003, D-006, D-007, D-008, D-009 | layout, toolchain, ASR transport, TTS gating, VAD role, portability | **RETAINED** — none depends on the deprecated dataset. |

## 7. Knowledge explicitly retained

Not touched by this reset, because it is independent of the deprecated dataset:

- The official problem statement (PS 26172) and all SIH framing
- **All ESP32-S3-WROOM-1-N16R8 hardware knowledge** — GPIO constraint table, PSRAM/flash
  facts, USB-Serial/JTAG identification, toolchain versions (`HARDWARE.md`)
- **All INMP441 knowledge** — electrical limits, I²S frame format, `L/R` behaviour
- The system architecture and its eight justified deviations (`ARCHITECTURE.md`)
- The evaluation methodology: streaming vs clip metrics, SWEEP/VALIDATE separation,
  host/device feature parity (`DECISIONS.md` D-005)
- All `[prior-build]` hardware evidence — inference timings, ESP-NN speedup, arena sizes
- The portability layer (`config/paths.py`, setup and verification scripts)
- `STORAGE_AUDIT.md` as a machine/storage record

## 8. Reset plan

1. `git rm` the six files in §5a.
2. Rewrite the two probes in §5b to be dataset-agnostic.
3. Rewrite the shared files in §5c to the dataset-first direction.
4. `DATASET.md` becomes a status page: **NOT YET CREATED**.
5. Deprecate D-002 and D-004 in place; add a new decision recording this reset.
6. Append the reset to `BUILD_LOG.md`.
7. Write `GIT_HISTORY_DATASET_PURGE.md` — analysis only, **no history rewrite performed**.
8. Quarantine the 674 MB on disk by renaming it out of the active path. **Not deleted** —
   deleting 674 MB of the user's data is the user's call, not mine.
9. Re-scan and verify no active reference survives.
