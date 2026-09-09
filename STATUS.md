# STATUS.md

**Last updated:** 2026-09-09 · **Phase:** **DATASET-FIRST RESTART**

> **The supplied dataset was deprecated and removed from the project** (`DECISIONS.md` D-010,
> `DATASET_RESET_AUDIT.md`). **There is no approved dataset and no selected keyword.**
> **Next:** keyword selection, then dataset design — `DATASET.md` §5.

**The repository is now machine-independent** (`DECISIONS.md` D-009). It can be cloned into
any directory on Windows or Linux; all paths resolve through `config/paths.py`. Start a new
machine from **`CURRENT_HANDOFF.md`**, which has a NEXT SESSION START block.

**Keyword settled:** **`Takshila`** (D-011). The dataset can now be specified and collected.

**Board status:** attached on **COM8 via a CH343 USB-UART bridge** — *not* the native
USB-Serial/JTAG the earlier COM5/COM7 records assumed. The audio capture path is **proven end
to end** (EXP-004). Port names and USB interfaces differ per board — never hard-code one.

---

## Where the project actually is

| Stage | State |
|---|---|
| Hardware + toolchain discovery | ✅ complete, retained |
| Architecture design | ✅ complete, retained |
| Project documentation | ✅ complete |
| Cross-machine portability + handoff | ✅ complete (D-009) |
| Machine setup / verification / health scripts | ✅ complete |
| **Keyword selected** | ✅ **`Takshila`** — confirmed, binding (D-011) |
| **Approved dataset** | ❌ **none — must be built from scratch** |
| Raw recordings collected | ❌ none |
| Python environment | ❌ not created (scripted: `scripts/setup.*`) |
| Firmware skeleton | 🟡 `firmware/platformio.ini` committed; **no source yet** |
| Feature pipeline | ❌ not written |
| Evaluation harness | ❌ not written |
| Model | ❌ none trained in this tree |
| On-device anything | ❌ nothing flashed in this tree |
| Streaming / ASR / UI | ❌ no code exists |

**Nothing has been measured on hardware in this tree.** Every hardware number currently in
`HARDWARE.md` is marked `[prior-build]` and is pending re-verification in Phase A.

---

## Blockers

### 🟢 B-1 — Pin map — RESOLVED 2026-09-09, and the audio path is PROVEN
Supplied map **SCK→GPIO 6 · WS→GPIO 5 · SD→GPIO 4 · VDD→3V3 · L/R→GND**, validated pin-by-pin
against `HARDWARE.md` §3 — **no conflict** — and encoded in
`firmware/include/hardware_config.h`. Identical to the prior build's wiring, now confirmed.

**Bring-up complete (EXP-004).** Measured on the real board: **16,001.50 Hz (+0.0094 %)**,
mono/PCM16, **bit alignment verified by measurement** (low 8 bits never set in 20,480 samples ⇒
24-in-32 left-justified, shift 16), **0 dropped blocks, 0 overruns, 0 clipped samples**,
5.000 s captures accurate to **+0.00 %**, valid WAV output, QC gate passing.

Two silent faults found and fixed: `Serial` was routed to an unconnected native USB CDC (this
board uses a **CH343 bridge on COM8**), and the first rate reading of +2.004 % was a DMA-ring
measurement bias, not the clock.

### 🟢 B-2 — ESP32 attached — RESOLVED 2026-09-09
`USB\VID_303A&PID_1001` now enumerates as USB Composite Device + **USB Serial Device (COM7)**
+ USB JTAG/serial debug unit, all `Status: OK`; `pio device list` reports
`VID:PID=303A:1001 SER=E0:72:A1:D7:20:24`. **The port is COM7, not the prior build's COM5.**
Nothing has been flashed and no chip readout has been performed — board identity (chip rev,
flash, PSRAM, heap) is still `[prior-build]` and is verified in **A4**.
**Unblocks:** A4–A6, F, I, and the device half of B4 — once B-1 (pin map) arrives.

### 🔴 B-3 — Wi-Fi credentials for the demo network
Router **192.168.1.1 confirmed reachable** from the host's Ethernet link (192.168.1.2/24).
The ESP32-S3 is **2.4 GHz only**.

**Refinement measured 2026-09-09:** the *host* does not need to join Wi-Fi at all. If the ESP32
joins the same router's 2.4 GHz SSID, the router bridges it to the wired LAN and it reaches the
server at 192.168.1.2 directly. So the only thing required is the **SSID + password of the
2.4 GHz network on that router** — no change to host networking.

Three Wi-Fi profiles were already stored on the original host; the one matching the router is
the likely candidate, but this is **not confirmed** and the stored key was deliberately **not**
read. *(SSID names are redacted here on purpose — network names are personally identifying and
this repository may be published. Put the real SSID and password in `.env` only, never in Git.)*
**Blocks:** Phase G3+.

Fallback is weaker than assumed: the adapter reports `Hosted network supported: No`, so the
legacy SoftAP path is unavailable; Windows Mobile Hotspot may still work via WiFi-Direct but
is untested.

### 🟢 B-5 — Keyword — RESOLVED 2026-09-09
**`Takshila`** /t̪əkˈʃiː.laː/ ("tuk-SHEE-laa") — **confirmed and binding**, `DECISIONS.md`
**D-011**, on the research in `KEYWORD_SELECTION.md` (18 candidates, weighted 20-criterion
matrix, phonetic + hard-negative analysis, licence audit, against Picovoice, Espressif ESP-SR,
FakeWake, Schönherr et al., Amazon's wake-word patent and Indian English phonology).

3 syllables · 7 phonemes · 4 manner classes · 5 places of articulation.
**Changing it later invalidates every recording made.** Do not reopen it.

### 🟡 B-6 — No dataset yet — **Tier-1 spec ready, collection blocked on B-1**
**Rescoped to a two-tier strategy (D-013).** The demo builds **Tier 1**
(`DEMO_DATASET_SPEC.md`): **6 speakers × 40 positives**, ~3.5 h of data work, minimum 3
speakers. The 30-speaker research programme moved to `RESEARCH_DATASET_ROADMAP.md` and **no
longer blocks the demo**.

**Collection still cannot start until B-1 is resolved** — 100 % of Tier-1 human positives must
be captured through the INMP441, because at this corpus size device match is the only domain
advantage available. Fallback if B-1 is unresolved at T+2 h: laptop capture with
`device_simulated=true`, which is materially worse and must be declared.

**Honesty obligation:** 6 speakers ⇒ **speaker-dependent-leaning**, test CI **±9.5 pp**, and a
3–6 h FA/hour figure is an order-of-magnitude statement. **No speaker-independence claim.**

**Blocks:** training, on-device KWS. **Does NOT block:** bring-up, server/UI scaffolding.

### 🟢 B-4 — C: free space — RESOLVED as far as is safely possible
Was 0 bytes. A cache-only cleanup on 2026-09-09 recovered **12.36 GB**; C: now holds
**12.84 GB free (10.85 %)**. Every tool was re-verified working afterwards (pip, npm,
PlatformIO, git, TensorFlow, project scripts). C: remains ~14 GB short of the ~27 GB needed to
host the project *and* keep Windows healthy, so the project stays on **E:** as one
self-contained tree — `DECISIONS.md` D-001, `STORAGE_AUDIT.md` §12. Caches regenerate with
use; re-running `STORAGE_AUDIT.md` §9 is safe and repeatable whenever C: gets tight.

---

## Open risks (not blockers)

| # | Risk | Note |
|---|---|---|
| R-1 | **Collecting a genuinely multi-speaker positive class is the hardest part of the new dataset** | It is also the one that decides the project. Plan it before recording — `DATASET.md` §2 |
| R-2 | A small test split gives a wide confidence interval on any rate | Size the test split deliberately during dataset design |
| R-3 | Speaker-independence is only claimable if the test split is **speaker-disjoint** | Build that into the split policy from the start |
| R-4 | Training may be **CPU-only** depending on the machine | Fine for a small DS-CNN; rules out large architecture searches |
| R-5 | Feature extraction over many small WAVs is I/O-bound on a HDD | Cache features to a single `.npz`; do not re-read audio each epoch |
| R-6 | Idle CPU will be high in Phase 1 | Declared Phase-2 debt, displayed on the dashboard (`DECISIONS.md` D-008) |
| R-7 | **Losing raw recordings would be unrecoverable** | The deprecated corpus could not be re-cut because its raw sessions were lost. **Keep every raw session** under `data/recordings` |

---

## Verified on the original machine (measured, not assumed)

> Dataset measurements previously listed here were removed with the dataset reset
> (`DECISIONS.md` D-010). They described the deprecated corpus and are out of scope.

- Host: i3-8100 4C/4T, 15.9 GB RAM, no CUDA, Windows 11 Pro 26200.
- Toolchain: PlatformIO 6.1.19, `espressif32@7.1.1`, Arduino core 2.0.17, **ESP-IDF 4.4**,
  Python 3.13.9 with TensorFlow 2.20.0.
- Network: Ethernet up at 192.168.1.2, internet reachable; Wi-Fi adapter present but disconnected.

---

## Immediate next actions

1. ~~Keyword selection~~ ✅ done — `Takshila` (D-011).
2. ~~Dataset specification~~ ✅ done — two tiers (D-013): **`DEMO_DATASET_SPEC.md`** builds now;
   `RESEARCH_DATASET_ROADMAP.md` is post-demo.
3. ~~Engine selection~~ ✅ done — **TFLM + ESP-NN** (D-012); ESP-SR unavailable, microWakeWord
   is the declared T+6 h fallback.
4. ~~Dataset tiering~~ ✅ done — **`DEMO_DATASET_SPEC.md`** is the build target (D-013).
5. ~~Resolve B-1~~ ✅ done — pin map validated, **audio path proven** (EXP-004).
6. **Finish the pilot:** record speech / `Takshila` / quiet / loud / near / far, then gate with
   `tools/audio_qc.py`. **This needs a voice at the microphone.**
7. Then Dataset Factory: record the **TEST speaker first** and quarantine it; start CS-WILD
   ambient capture and Piper hard-negative generation early — both run unattended.
3. **In parallel, hardware-side and dataset-independent:** environment setup (A1), the
   PlatformIO skeleton (A2), and — once the pin map arrives — bring-up A3–A6.
4. **Still needed from the user:** the authoritative pin map (**B-1**) and the 2.4 GHz Wi-Fi
   SSID + password (**B-3**).
5. Resolved: board attached (B-2), C: free space (B-4).
