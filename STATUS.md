# STATUS.md

**Last updated:** 2026-09-09 · **Phase:** Discovery + bootstrap **COMPLETE**
**Next:** `BUILD_PLAN.md` Phase A1–A2 and Phase B (neither needs hardware).

---

## Where the project actually is

| Stage | State |
|---|---|
| Discovery (docs, dataset, hardware, toolchain) | ✅ complete |
| Project documentation bootstrapped | ✅ complete |
| Python environment | ❌ not created |
| Firmware skeleton | ❌ not created |
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

### 🔴 B-2 — The ESP32 is not attached to this host
No `VID_303A` USB device is enumerated; the only serial port present is a legacy ACPI `COM1`.
The prior build used COM5. **Blocks:** every on-device task (A4–A6, F, I, and G3–G6).
**Not blocking:** Phases B, C, D, E, H — about 9 of the 16 planned hours.

### 🔴 B-3 — Wi-Fi credentials for the demo network
The host's only live link is Ethernet at `192.168.1.2/24`, implying a router at
`192.168.1.1`. The ESP32-S3 is **2.4 GHz only**. Needed: SSID + password of a 2.4 GHz network
the host can also reach. Fallback: Windows Mobile Hotspot. **Blocks:** Phase G3+.

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

1. **Unblocked, start now:** A1 (venv on E:), A2 (PlatformIO skeleton), then Phase B and C.
2. **Needed from the user:** the authoritative pin map (B-1), the board plugged in (B-2),
   Wi-Fi SSID/password (B-3).
3. **Recommended:** free a few GB on C: (B-4).
