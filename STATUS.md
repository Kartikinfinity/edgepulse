# STATUS.md

**Last updated:** 2026-09-09 · **Phase:** Discovery + bootstrap **COMPLETE**; storage/environment
prep **COMPLETE**; transition verification **PASSED**; **cross-machine handoff prepared**.
**Next:** `BUILD_PLAN.md` **A1–A2**, then **B**, then **C**. Awaiting the user's go-ahead.

**The repository is now machine-independent** (`DECISIONS.md` D-009). It can be cloned into
any directory on Windows or Linux; all paths resolve through `config/paths.py`. Start a new
machine from **`CURRENT_HANDOFF.md`**, which has a NEXT SESSION START block.

**Board status:** the ESP32 was attached on **COM7 on the original machine** (B-2 resolved
there). Port names differ per machine — never hard-code one.

---

## Where the project actually is

| Stage | State |
|---|---|
| Discovery (docs, dataset, hardware, toolchain) | ✅ complete |
| Project documentation bootstrapped | ✅ complete |
| Cross-machine portability + handoff | ✅ complete (D-009) |
| Machine setup / verification / health scripts | ✅ complete |
| Committed dataset fingerprint (`dataset_manifest/`) | ✅ complete |
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

### 🔴 B-1 — Authoritative pin map not yet supplied
The user stated the exact INMP441 to ESP32-S3 pin mapping would be provided separately and is
authoritative. Until it arrives, `HARDWARE.md` section 4 holds only the prior build's wiring,
marked UNCONFIRMED. **Blocks:** A3, and therefore all of Phase A5+ and Phase F.
**Validation ready:** `HARDWARE.md` section 3 has the full constraint table (GPIO 35/36/37 are
tied to Octal PSRAM on this module and must not be used; 0/3/45/46 are strapping pins).

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
| R-1 | **Positive class = 110 utterances, one speaker, two rooms** | The project's binding constraint. `DECISIONS.md` D-004, `BUILD_PLAN.md` Phase D |
| R-2 | Test split has **17** positive utterances | ~±20 pp confidence interval; the streaming harness is the real bar |
| R-3 | No speaker-independence is possible from this data | No such claim may be made |
| R-4 | Training is **CPU-only** (Intel UHD 630, no CUDA) | Fine for a small DS-CNN; rules out large architecture searches |
| R-5 | E: is a HDD | Cache features to `.npz`; do not re-read 21k WAVs per epoch |
| R-6 | Idle CPU will be ~48 % in Phase 1 | Declared Phase-2 debt, displayed on the dashboard (`DECISIONS.md` D-008) |
| R-7 | The raw uncut recordings (`Desktop/data/`) are **confirmed absent from all three drives** — four independent searches, `STORAGE_AUDIT.md` §11 | Positives cannot be re-cut at new offsets; `DATASET.md` §9. `D:\speech_commands` (5.37 GB, Speech Commands v0.02) *is* present and usable for negatives/background |

---

## Verified in this session (measured here, not assumed)

- Dataset: 21,267 WAVs; **100 %** of a 1,500-file random sample is mono / 16 kHz / 16-bit /
  exactly 16,000 frames. 0 files missing against the manifests.
- Split leakage: **0 of 2,387** source recordings appear in more than one split, in either
  dataset variant. The split is genuinely recording-disjoint.
- Positives: 790 clips from **110 unique recordings**, `speaker_01` only, environments
  `fan` (60) and `classroom` (50).
- Keyword position: ~545 ms active span, peak-bin std ±255 ms — loosely centred with real spread.
- Speech-band energy fraction: positive 0.561 / negative 0.662 / **background 0.538**.
- Host: i3-8100 4C/4T, 15.9 GB RAM, no CUDA, Windows 11 Pro 26200.
- Toolchain: PlatformIO 6.1.19, `espressif32@7.1.1`, Arduino core 2.0.17, **ESP-IDF 4.4**,
  Python 3.13.9 with TensorFlow 2.20.0.
- Network: Ethernet up at 192.168.1.2, internet reachable; Wi-Fi adapter present but disconnected.

---

## Immediate next actions

1. **Unblocked, ready to start:** A1 (venv on E:), A2 (PlatformIO skeleton with `upload_port`
   = **COM7** and `build_dir` on E:), then Phase B and Phase C.
2. **Still needed from the user:** the authoritative pin map (**B-1**) and the 2.4 GHz Wi-Fi
   SSID + password (**B-3**).
3. Resolved: board attached (B-2), C: free space (B-4).
