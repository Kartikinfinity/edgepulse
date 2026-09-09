# CLAUDE.md — orientation for any session in this repository

**Project:** SIH 2026 · PS **26172** — *Low Latency and Efficient Voice Activator for Edge Devices* (ISRO / Dept. of Space)
**Keyword:** **`Takshila`** /t̪əkˈʃiː.laː/ ("tuk-SHEE-laa") — confirmed and binding, `DECISIONS.md` D-011.
**Phase:** **Dataset-first restart.** Keyword settled; **no dataset exists yet** (D-010).

---

## 0. Inspect these before acting — in this order

1. `CURRENT_HANDOFF.md` — the practical entry point. Has a **NEXT SESSION START** block.
2. `PROJECT_STATE.md` — what exists and what does not.
3. `BUILD_PLAN.md` — the phase you are in and its exit bar.
4. `DECISIONS.md` — why things are the way they are. Do not re-litigate these.
5. `EXPERIMENT_STATE.md` — what has actually been measured, and what has not.
6. Then the topic doc you need: `ARCHITECTURE.md`, `DATASET.md`, `HARDWARE.md`.

Then run, before writing any code:

```bash
python scripts/verify_setup.py      # is this machine ready?
python scripts/health_check.py      # git state, phase progress, blockers
```

---

## 1. Project objective

Build a complete, demonstrable hybrid edge/cloud voice activator:

```
INMP441 --I2S/DMA--> ring buffer --> VAD --> MFCC --> int8 DS-CNN (TFLM + ESP-NN)
   --> M-of-N smoothing --> WAKE --> pre-roll + live PCM --WebSocket/Wi-Fi-->
   server --> ASR (faster-whisper) --> transcript --> intent/action --> live dashboard
```

The wake word is detected **locally on the ESP32-S3**; only after detection is
audio streamed to a **remote ASR server**. The live demo UI is a first-class
deliverable, not an afterthought.

Full design and the eight justified deviations from the supplied plan:
`ARCHITECTURE.md`. The supplied architecture documents are the **baseline, not
an immutable specification** — improve them where there is a technical
justification, but state the deviation and the reason.

## 2. Hardware

| Item | Value |
|---|---|
| MCU | ESP32-S3-WROOM-1-**N16R8** — 16 MB quad flash, 8 MB **octal** PSRAM, dual LX7 @ 240 MHz |
| Microphone | INMP441 I²S MEMS — 24-bit, 64 SCK per WS frame, **VDD 1.8–3.3 V, NEVER 5 V** |
| Link | native USB-Serial/JTAG, `VID:PID 303A:1001` |
| Toolchain | PlatformIO `espressif32@7.1.1`, Arduino core 2.0.17, ESP-IDF 4.4, legacy `driver/i2s.h` |

**GPIO 35/36/37 are wired to the Octal PSRAM on this module and must never be
used.** Also unavailable: 26–32 (flash), 0/3/45/46 (strapping), 19/20 (USB),
43/44 (UART0), 22–25 (do not exist). Full table: `HARDWARE.md` §3.

**The authoritative pin map has not been supplied.** It is blocker **B-1** and
gates all hardware work. Validate it against `HARDWARE.md` §3 when it arrives.

Serial port names differ per machine — the original host used COM7, Linux will
use `/dev/ttyACM0`. **Never hard-code a port.** Let PlatformIO auto-detect or
set `SIH_UPLOAD_PORT` in `.env`.

## 3. Dataset — THERE IS NONE YET

```
DATASET STATUS: NOT YET CREATED
KEYWORD:        "Takshila" - CONFIRMED (D-011)
DATASET SPEC:   COMPLETE - DATASET_SPEC.md (frozen, 37 sections)
NEXT OBJECTIVE: resolve B-1 (pin map) -> build recorder -> ONE measured
                pilot session -> collect.
```

**Keyword facts you will need constantly.** `Takshila` = 3 syllables, 7 phonemes,
CVC·CV·CV. Its hard negatives are the **क्ष family** (*shiksha, raksha, lakshya, moksha*)
and the **/tæks/ family** (*taxi, tax, tactical, taxonomy*) — both must be in **training**,
not only in test. Full analysis and the complete data specification: `KEYWORD_SELECTION.md`.

The previously supplied corpus was **deprecated and removed** (`DECISIONS.md` D-010,
`DATASET_RESET_AUDIT.md`). It must not be used for training, validation, testing,
benchmarking, statistics, augmentation design, keyword selection, or any conclusion.
Its numbers are out of scope — do not quote them, even from memory.

Full status and the plan: **`DATASET.md`**.

### The design principle carried forward from why the old corpus failed

> A positive class recorded from **one speaker** cannot be repaired downstream.
> Augmentation copies information; it does not add any. A predecessor demonstrated
> **on hardware** that neither decision-logic tuning nor more public negative speech
> fixes it.

So for the dataset you are about to design: **speaker diversity in the positive class is
the primary design variable**, raw uncut recordings must be kept, positional spread must
be deliberate, and splits must be **speaker-disjoint**. `DATASET.md` §2 states these as
requirements.

## 4. Constraints

**In scope this phase:** real-world KWS accuracy, false-trigger resistance,
detection reliability, end-to-end functionality, latency, output quality, live
demo reliability.

**Explicitly OUT OF SCOPE this phase — by instruction:**

- the <256 KB RAM budget
- the <10 % idle CPU budget

Do **not** optimise around those two numbers, reject an architecture because of
them, or quantise/prune/compress to satisfy them. **Do** measure and display
both honestly on the dashboard; `ARCHITECTURE.md` §9 records the Phase-2 debt.

Also binding, from the problem statement: **open-source only**, no proprietary
voice-activation SDKs, and **no models pre-trained on generic smart-assistant
keywords**. The keyword must be **custom** — which is a live constraint on the
keyword-selection task now in front of you, not a settled fact.

## 5. Safety rules — non-negotiable

1. **Measure, then claim.** Every number in a document names its source. If it
   was not measured, write "not measured". Never fabricate or round up a result.
2. **Evaluate the way the device runs.** Sliding windows over continuous audio,
   never centred 1.0 s clips. A clip-level figure is **not** a detector figure.
   These five are different things and must never be conflated:
   clip classification · streaming detection · false-trigger rate ·
   wake-word latency · real-world robustness. (`DECISIONS.md` D-005)
3. **A number swept and judged on the same audio is provisional, not a result.**
   Sweep on SWEEP, validate on a disjoint VALIDATE set.
4. **Feature parity is mandatory.** Host and device MFCC must match numerically
   before any on-device accuracy claim.
5. **Anything tagged `[prior-build]` is evidence from a *different* project**
   (keyword "Sentinel"). Re-verify before quoting it as a result here.
   Likewise, **the deprecated corpus' statistics are out of scope entirely** —
   they may not be quoted even as background (`DECISIONS.md` D-010).
6. **One change per experiment**, logged in `BUILD_LOG.md` with a pre-declared
   pass bar and a mandatory "what this does NOT prove" section.
7. **If a result looks surprisingly good, suspect the evaluation before the
   model.** That instinct has been correct every time on this project.
8. **Never commit secrets** — Wi-Fi credentials, tokens, keys. They belong in
   `.env`, which is git-ignored.
9. **Never commit audio or model artifacts.** Once the new dataset exists it gets a
   committed fingerprint (counts + checksums); the audio itself stays out of Git.

## 6. Paths — the repository is machine-independent

**There is no fixed project root.** The repo works from any directory on Windows
or Linux. Everything resolves through `config/paths.py`, which derives the root
from its own location.

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import DATASET_ROOT, ARTIFACTS_DIR, PROJECT_ROOT
```

| What | Where |
|---|---|
| Project root | derived at runtime — never hard-code it |
| Dataset (to be built) | `<root>/data/dataset` or `SIH_DATASET_ROOT` — **does not exist yet** |
| Raw recordings (keep!) | `<root>/data/recordings` or `SIH_RECORDINGS_ROOT` |
| Features / checkpoints / models | `<root>/artifacts` (git-ignored) |
| Python venv | `<root>/.venv` (git-ignored) |
| Firmware build output | `<root>/firmware/.pio` (git-ignored) |
| PlatformIO core (toolchains) | per-machine tool install, outside the repo — that is correct |
| Machine-specific settings | `<root>/.env`, copied from `.env.example` |

**Never write an absolute path into tracked source.** `E:\sih2026`, `C:\Users\…`
and drive letters appear only inside historical records (`STORAGE_AUDIT.md`,
`BUILD_LOG.md`, parts of `DECISIONS.md`), where they document what was true on
one machine on one date and must not be edited into fiction.

> **Windows/Python trap, already paid for once.** A Git-Bash POSIX path such as
> `/e/some/dir` is **not** understood by a native Windows Python — it resolves
> `/e/...` against the *current* drive (`C:\e\...`) and silently fills that disk.
> Pass Windows paths to Windows Python and POSIX paths to bash tools. Better:
> use `config/paths.py`, which returns correct `Path` objects on both platforms
> and makes the question moot.

> **Python 3.14 does not work** — TensorFlow publishes no wheels for it. Use
> 3.10–3.13.

## 7. Commands

```bash
# setup (once per machine)
bash scripts/setup.sh --dev                                      # Linux/macOS/Git Bash
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Dev  # Windows

# verification
python scripts/verify_setup.py          # machine readiness
python scripts/health_check.py          # git state, phase progress, blockers

# audio measurement (dataset-agnostic; point at any directory of WAVs)
python tools/audio_probe.py <dir>         # format, duration, level, clipping
python tools/audio_probe_bands.py <dir>   # speech-band energy; where the word sits

# tests
python -m pytest

# firmware (needs firmware/src/, which does not exist yet)
cd firmware && pio run
pio run -t upload
pio device monitor
```

## 8. Current priorities — dataset-first

1. ~~Keyword selection~~ ✅ **DONE — `Takshila` (D-011).** Do not reopen it.
2. ~~Dataset design specification~~ ✅ **DONE — `KEYWORD_SELECTION.md` §§13–15.** Use it;
   do not redesign it.
3. ~~Dataset specification~~ ✅ **DONE — `DATASET_SPEC.md`, frozen.** Build from it; do not
   redesign it.
4. **Resolve B-1 (pin map)** — now the critical-path blocker: ≥70 % of positives must be
   recorded on the real INMP441, so collection cannot start without it.
5. **Recorder + ONE measured pilot session** before recruiting anyone — the current task.
4. Collection — **keeping every raw session**, speaker IDs recorded from the first file.
5. Curate, build, version and fingerprint the dataset.
6. **Only then**: features, the streaming evaluation harness (before any model), training.

Hardware bring-up (`BUILD_PLAN.md` Phase A) is independent of the dataset and may proceed
in parallel once the pin map arrives.

**Open blockers:** **B-1** authoritative pin map · **B-3** 2.4 GHz Wi-Fi credentials ·
**B-6** no dataset. (**B-5** keyword — resolved.) Live detail in `STATUS.md`.

## 9. What NOT to redo

Re-deriving settled work is the most likely way to waste this project's budget.
The short version, updated for the dataset-first restart: do not use or cite the
deprecated corpus for anything; do not report clip accuracy as detector accuracy; do not
migrate the toolchain without a measured reason; do not optimise for the two out-of-scope
resource budgets; and do not re-derive the hardware constraints or the architecture —
both survived the reset intact and are recorded.
