# PROJECT_STATE.md

A single factual snapshot of everything this repository contains and does not
contain. `CURRENT_HANDOFF.md` tells you what to *do*; this file tells you what
*is*.

Snapshot date: **2026-09-09** · Regenerate the live view with
`python scripts/health_check.py`.

---

## 1. Identity

| Field | Value |
|---|---|
| Competition | Smart India Hackathon 2026 |
| Problem statement | **PS 26172** — *Low Latency and Efficient Voice Activator for Edge Devices* |
| Organisation | ISRO / Department of Space |
| Keyword | **`solvani`** (sol-vaa-nee) |
| Target hardware | ESP32-S3-WROOM-1-N16R8 + INMP441 I²S MEMS microphone |
| Build phase | **Phase 1** — maximum practical accuracy, robustness and demo quality |
| Explicitly out of scope this phase | <256 KB RAM, <10 % idle CPU (measured and displayed, **not** optimised for) |

## 2. Repository inventory

### Documentation (all committed, all current)

| File | Purpose |
|---|---|
| `CLAUDE.md` | Orientation + safety rules for an AI session. Read first. |
| `README.md` | Project overview |
| `CURRENT_HANDOFF.md` | **Cross-machine handoff. The practical entry point.** |
| `PROJECT_STATE.md` | This file — what exists |
| `STATUS.md` | Live status, blockers, open risks |
| `BUILD_PLAN.md` | Phases A–I with per-phase exit bars |
| `ARCHITECTURE.md` | System design + 8 justified deviations from the supplied plan |
| `DATASET.md` | Measured dataset analysis |
| `DATASET_SETUP.md` | How to obtain and verify the dataset on a new machine |
| `HARDWARE.md` | Board, microphone, GPIO constraints, host, toolchain |
| `ENVIRONMENT_SETUP.md` | Windows + Linux machine setup |
| `EXPERIMENT_STATE.md` | Experiment ledger — what has been measured and what has not |
| `DECISIONS.md` | D-001…D-009, irreversible decisions with reasoning |
| `BUILD_LOG.md` | Append-only log with pre-declared pass bars |
| `STORAGE_AUDIT.md` | Historical record of the original machine's storage work |

### Code

| Path | Contents | State |
|---|---|---|
| `config/paths.py` | machine-independent path + setting resolution | ✅ working |
| `tools/analyze_manifests.py` | dataset structure + leakage analysis | ✅ working |
| `tools/audio_probe.py` | audio format + envelope probe | ✅ working |
| `tools/audio_probe_bands.py` | band-limited keyword localisation | ✅ working |
| `scripts/setup.sh` / `setup.ps1` | one-shot environment setup | ✅ working |
| `scripts/verify_setup.py` | machine readiness check | ✅ working |
| `scripts/verify_dataset.py` | dataset integrity vs committed manifest | ✅ working |
| `scripts/health_check.py` | project state report | ✅ working |
| `scripts/generate_dataset_manifest.py` | regenerate the dataset fingerprint | ✅ working |
| `training/` | feature pipeline, training, streaming eval | ❌ **empty** |
| `firmware/src/` | ESP32 firmware | ❌ **empty** |
| `server/` | ASR + WebSocket + intent | ❌ **empty** |
| `ui/` | demo dashboard | ❌ **empty** |
| `tests/` | — | ❌ **does not exist** |

### Configuration

| File | Purpose |
|---|---|
| `.env.example` | template for machine-specific settings (copy to `.env`) |
| `.gitignore` | secrets, venvs, caches, build output, dataset, artifacts |
| `requirements.txt` | numpy, scipy, soundfile, tensorflow |
| `requirements-dev.txt` | pytest, matplotlib, librosa |
| `requirements-server.txt` | faster-whisper, websockets (Phase G) |
| `pyproject.toml` | pytest/ruff config, project metadata |
| `firmware/platformio.ini` | pinned ESP32 build config — **no source yet** |

### Generated metadata

| File | Purpose |
|---|---|
| `dataset_manifest/manifest.json` | counts, structure, per-CSV and root SHA-256 |
| `dataset_manifest/CHECKSUMS.sha256` | 21,285 per-file SHA-256 digests |

### Not in Git, by design

`data/` (0.64 GB dataset) · `artifacts/` (features, checkpoints, models) ·
`.venv/` · `.pio/` · `.env` · any credential.

## 3. Model artifacts

**None.** No model has been trained in this repository. No `.tflite`, `.keras`,
`.h5` or `.npz` exists. Any model numbers you find in the documents are labelled
`[prior-build]` and belong to a **different project with a different keyword**
("Sentinel"), kept only as engineering evidence.

## 4. Experiment results

See `EXPERIMENT_STATE.md`. Summary: two operational records (OPS-001, OPS-002)
and one discovery record (EXP-000). **Zero ML experiments. Zero hardware
measurements taken in this tree.**

## 5. Phase progress against BUILD_PLAN.md

| Phase | Description | State |
|---|---|---|
| A1 | Python venv | ⚪ scripted, not yet run on the target machine |
| A2 | PlatformIO skeleton | 🟡 `platformio.ini` committed; no `src/` yet |
| A3 | Apply authoritative pin map | 🔴 **blocked — pin map not supplied** |
| A4–A6 | Board identity, I²S capture, sample-rate measurement | ⚪ not started (needs A3) |
| B | Feature pipeline + parity | ⚪ not started |
| C | Streaming evaluation harness | ⚪ not started |
| D | Positive-class work | ⚪ not started |
| E | Model, quantisation, export | ⚪ not started |
| F | On-device KWS | ⚪ not started |
| G | Streaming + ASR server | ⚪ not started (also needs Wi-Fi credentials) |
| H | Demo UI | ⚪ not started |
| I | Validation + rehearsal | ⚪ not started |

Roughly **9 of the 16 planned hours (B, C, D, E, H) need no hardware at all.**

## 6. Blockers

| # | Blocker | Blocks |
|---|---|---|
| **B-1** | Authoritative INMP441 → ESP32-S3 pin map not supplied | A3 → A4–A6, F, I |
| **B-3** | 2.4 GHz Wi-Fi SSID + password | G3 onward |
| B-2 | ✅ resolved — board attached (COM7 on the original machine) | — |
| B-4 | ✅ resolved — storage recovered on the original machine | — |

## 7. Open TODOs

1. Run `scripts/setup.sh` / `setup.ps1` on the new machine (A1).
2. Add `firmware/src/main.cpp` so `pio run` produces a binary (A2).
3. Write `training/features.py` + tests (B1).
4. Build the streaming evaluation harness (C) **before any model**.
5. Obtain the pin map (B-1) and the Wi-Fi credentials (B-3) from the user.
6. Optional but highest-value: record 3–5 additional speakers (D6).

## 8. The finding that governs the whole project

> **21,267 WAV files, but only ~110 unique positive utterances from one speaker.**

Augmentation inflated 110 recordings into 790 positive clips; the negative class
draws on thousands of speakers. This asymmetry — not architecture, not
quantisation, not threshold tuning — is what decides whether the system works.

It also forces a discipline the project must not relax: **clip-level
classification metrics, streaming detector metrics, false-trigger behaviour,
wake-word latency and real-world robustness are five different things** and must
never be reported as one. `DECISIONS.md` D-004 and D-005.
