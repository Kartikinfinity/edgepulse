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
| Keyword | **`Takshila`** /t̪kˈʃiː.laː/ — confirmed, binding (D-011) |
| Target hardware | ESP32-S3-WROOM-1-N16R8 + INMP441 I²S MEMS microphone |
| Build phase | **Dataset-first restart** — keyword settled; no dataset yet |
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
| `DATASET.md` | **Dataset status (NOT YET CREATED) + the plan to build one** |
| `DATASET_RESET_AUDIT.md` | The audit behind the dataset reset |
| `GIT_HISTORY_DATASET_PURGE.md` | Why no history rewrite is needed |
| `HARDWARE.md` | Board, microphone, GPIO constraints, host, toolchain |
| `ENVIRONMENT_SETUP.md` | Windows + Linux machine setup |
| `EXPERIMENT_STATE.md` | Experiment ledger — what has been measured and what has not |
| `DECISIONS.md` | D-001…D-011, irreversible decisions with reasoning |
| `KEYWORD_SELECTION.md` | Keyword research: 18 candidates, scoring, phonetics, licence audit |
| `DEMO_DATASET_SPEC.md` | **Tier 1 — the dataset being built NOW (6 speakers)** |
| `RESEARCH_DATASET_ROADMAP.md` | Tier 2 — post-demo research-grade target (30 speakers) |
| `KWS_ENGINE_DECISION.md` | **Engine choice, pipeline verification, keyword lock** |
| `BUILD_LOG.md` | Append-only log with pre-declared pass bars |
| `STORAGE_AUDIT.md` | Historical record of the original machine's storage work |

### Code

| Path | Contents | State |
|---|---|---|
| `config/paths.py` | machine-independent path + setting resolution | ✅ working |
| `tools/audio_probe.py` | **dataset-agnostic** format / level / clipping probe | ✅ working |
| `tools/audio_probe_bands.py` | **dataset-agnostic** speech-band + word-position probe | ✅ working |
| `scripts/setup.sh` / `setup.ps1` | one-shot environment setup | ✅ working |
| `scripts/verify_setup.py` | machine readiness check | ✅ working |
| `scripts/health_check.py` | project state report | ✅ working |
| `training/` | feature pipeline, training, streaming eval | ❌ **empty** |
| `firmware/src/` | ESP32 firmware | ❌ **empty** |
| `server/` | ASR + WebSocket + intent | ❌ **empty** |
| `ui/` | demo dashboard | ❌ **empty** |
| `tests/` | — | ❌ **does not exist** |

### Configuration

| File | Purpose |
|---|---|
| `.env.example` | template for machine-specific settings (copy to `.env`) |
| — | *dataset verification tooling was removed with the reset; it will be rebuilt once the new dataset's structure is known* |
| `.gitignore` | secrets, venvs, caches, build output, dataset, artifacts |
| `requirements.txt` | numpy, scipy, soundfile, tensorflow |
| `requirements-dev.txt` | pytest, matplotlib, librosa |
| `requirements-server.txt` | faster-whisper, websockets (Phase G) |
| `pyproject.toml` | pytest/ruff config, project metadata |
| `firmware/platformio.ini` | pinned ESP32 build config — **no source yet** |

### Generated metadata

**None.** The previous dataset fingerprint was removed with the reset. A new one will be
generated once a dataset exists and its structure is known.

### Not in Git, by design

`data/` (recordings + built dataset — neither exists yet) · `artifacts/` ·
`.venv/` · `.pio/` · `.env` · any credential.

## 3. Model artifacts

**None.** No model has been trained in this repository. No `.tflite`, `.keras`,
`.h5` or `.npz` exists. Any model numbers you find in the documents are labelled
`[prior-build]` and belong to a **different project with a different keyword**
("Sentinel"), kept only as engineering evidence.

## 4. Experiment results

See `EXPERIMENT_STATE.md`. Summary: three operational records (OPS-001…003) and one discovery
record (EXP-000, whose **dataset findings are voided** by D-010). **Zero ML experiments. Zero
hardware measurements taken in this tree.**

## 5. Phase progress against BUILD_PLAN.md

| Phase | Description | State |
|---|---|---|
| **0.1** | **Keyword selection** | DONE — **`Takshila` (D-011)** |
| **0.2** | **Dataset specification** | DONE — **two tiers (D-013)** |
| **0.2b** | **KWS engine selection** | DONE — **TFLM + ESP-NN (D-012)** |
| **0.3–0.5** | **Recorder, pilot, collection, build** | blocked on **B-1 (pin map)**; blocks B–F |
| A1 | Python venv | ⚪ scripted, not yet run on the target machine |
| A2 | PlatformIO skeleton | 🟡 `platformio.ini` committed; no `src/` yet |
| A3 | Apply authoritative pin map | 🔴 **blocked — pin map not supplied** |
| A4–A6 | Board identity, I²S capture, sample-rate measurement | ⚪ not started (needs A3) |
| B | Feature pipeline + parity | 🔴 blocked — needs a dataset |
| C | Streaming evaluation harness | 🔴 blocked — needs a dataset |
| D | Positive-class work | 🔴 blocked; may be unnecessary if Phase 0 is done well |
| E | Model, quantisation, export | 🔴 blocked — needs a dataset |
| F | On-device KWS | ⚪ not started |
| G | Streaming + ASR server | ⚪ not started (also needs Wi-Fi credentials) |
| H | Demo UI | ⚪ not started |
| I | Validation + rehearsal | ⚪ not started |

Phase A (hardware bring-up) and Phase H (UI, simulator-driven) are the only phases that are
**neither dataset-blocked nor, for H, hardware-blocked**. Everything else waits on Phase 0.

## 6. Blockers

| # | Blocker | Blocks |
|---|---|---|
| B-5 | resolved — keyword `Takshila` confirmed (D-011) | — |
| **B-6** | **No approved dataset** | B, C, D, E, F, I |
| **B-1** | Authoritative INMP441 → ESP32-S3 pin map not supplied | A3 → A4–A6, F, I |
| **B-3** | 2.4 GHz Wi-Fi SSID + password | G3 onward |
| B-2 | ✅ resolved — board attached (COM7 on the original machine) | — |
| B-4 | ✅ resolved — storage recovered on the original machine | — |

## 7. Open TODOs

1. ~~Keyword selection~~ **DONE** — **`Takshila`** (D-011).
2. ~~Dataset design specification~~ **DONE** — `KEYWORD_SELECTION.md` §§13–15.
3. **Write the recording protocol and run ONE pilot session**, measured with
   `tools/audio_probe.py` and `tools/audio_probe_bands.py`, **before recruiting speakers**
   (Phase 0.3). This is the current task.
4. In parallel, dataset-independent: `scripts/setup.*` (A1) and `firmware/src/main.cpp` so
   `pio run` produces a binary (A2).
5. Obtain the pin map (B-1) and the Wi-Fi credentials (B-3) from the user.

## 8. The principle that governs the whole project

> **A positive class recorded from one speaker cannot be repaired downstream.**
> Augmentation copies information; it does not add any.

A predecessor demonstrated on hardware that neither decision-logic tuning nor more public
negative speech fixes it. That is why this project now restarts dataset-first, with **speaker
diversity in the positive class as the primary design variable** — planned before recording,
not discovered afterwards.

It also forces a discipline the project must not relax: **clip-level classification, streaming
detection, false-trigger behaviour, wake-word latency and real-world robustness are five
different things** and must never be reported as one. `DECISIONS.md` D-005.
