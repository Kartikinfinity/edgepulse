# HARDWARE.md

Status legend: **[measured-here]** verified in this tree · **[prior-build]** measured in the
previous "Sentinel" build, must be re-verified · **[datasheet]** vendor document ·
**[UNCONFIRMED]** claim awaiting authority.

---

## 1. Target board

| Item | Value | Source |
|---|---|---|
| Module | ESP32-S3-WROOM-1-**N16R8** | [prior-build] eFuse readout (quad flash @3.3 V ⇒ WROOM-1, not WROOM-2 N16R8V) |
| SoC | ESP32-S3 (QFN56) rev v0.2, dual Xtensa LX7 @ 240 MHz | [prior-build] `esp_chip_info()` |
| Flash | 16 MB **Quad** SPI | [datasheet] Table 1; [prior-build] `esp_flash_get_size()` |
| PSRAM | 8 MB **Octal** SPI | [datasheet] Table 1; [prior-build] `psramFound()` = true, 8,386,231 B |
| Internal SRAM (heap) | 394,924 B total / 370,680 B free at boot | [prior-build] |
| Link | Native USB-Serial/JTAG, USB VID:PID `303A:1001` | [prior-build] |
| Port | **COM7** | **[measured-here] 2026-09-09** — `USB VID:PID=303A:1001 SER=E0:72:A1:D7:20:24 LOCATION=1-5:x.0`, enumerated as "USB Serial Device (COM7)" + "USB JTAG/serial debug unit". **The prior build used COM5; the port number has changed — do not hard-code COM5.** |

## 2. Microphone — INMP441

| Parameter | Value | Source |
|---|---|---|
| Interface | I²S, **24-bit**, two's complement, MSB-first | [datasheet] p.13 |
| Frame format | **64 SCK cycles per WS frame**, 32 SCK per data word | [datasheet] p.13 |
| Supply VDD | **1.8 – 3.3 V** — ⚠ **never 5 V** (abs max VDD+0.3 V / 3.63 V) | [datasheet] Table 1, Abs Max |
| Supply current | 1.4 mA typ, 1.6 mA max (normal mode) | [datasheet] Table 1 |
| Sensitivity | −26 dBFS @ 94 dB SPL, 1 kHz (−29 … −23) | [datasheet] Table 1 |
| SNR | 61 dBA | [datasheet] features |
| Frequency response | −3 dB at 60 Hz and 15 kHz (flat between) | [datasheet] Table 1 |
| `L/R` pin | **LOW ⇒ mic drives the LEFT channel**; HIGH ⇒ right | [datasheet] pin 4 description |
| `CHIPEN` | Must be HIGH for the mic to run | [datasheet] pin 8 |
| Logic thresholds | V_IH ≥ 0.7 × VDD, V_IL ≤ 0.25 × VDD | [datasheet] Table 2 |

**Pinout (physical part):** 1 SCK · 2 SD · 3 WS · 4 L/R · 5 GND · 6 GND · 7 VDD · 8 CHIPEN · 9 GND.

At 16 kHz with 64 SCK/frame, **SCK = 1.024 MHz**.

## 3. GPIO availability on this exact module — authoritative constraint list

Use this to **validate** the pin map when it arrives.

| GPIO | Status | Source |
|---|---|---|
| **35, 36, 37** | ❌ **Connected to the Octal SPI PSRAM on R8 modules — not available for other uses** | [datasheet] WROOM-1 Table 3-1 footnote *b* |
| 26 – 32 | ❌ SPI flash bus (internal to the module) | [datasheet] module schematic |
| 19, 20 | ⚠ USB D− / D+ — using them kills the native USB console | [datasheet] |
| 43, 44 | ⚠ UART0 TXD/RXD | [datasheet] Table 3-1 |
| **0, 3, 45, 46** | ⚠ **Strapping pins** (boot mode, VDD_SPI voltage, ROM print) — avoid | [datasheet] Table 4-1 |
| 22, 23, 24, 25 | ❌ Do not exist on ESP32-S3 | [datasheet] |
| 47, 48 | ✅ Available at 3.3 V on N16R8 (1.8 V only on R16V) | [datasheet] footnote *c* |
| 1,2,4–18,21,38–42 | ✅ Generally free (38–42 also carry JTAG MTMS/MTDI/MTDO/MTCK) | [datasheet] |

## 4. Wiring — ✅ **CONFIRMED 2026-09-09**

**Supplied by the user as the verified physical wiring of the actual hardware.** Validated
pin-by-pin against §3 below: **no conflict**. Encoded once, authoritatively, in
`firmware/include/hardware_config.h` — nothing else in the project may define a GPIO number.

| INMP441 | ESP32-S3 | Role | §3 check |
|---|---|---|---|
| SCK | **GPIO 6** | I²S bit clock (BCLK), ESP32 → mic | ✅ free |
| WS | **GPIO 5** | I²S word select (LRCLK), ESP32 → mic | ✅ free |
| SD | **GPIO 4** | I²S data in, mic → MCU | ✅ free |
| VDD | **3V3** | supply — 1.8–3.3 V part, abs max 3.63 V. **Never 5 V** | ✅ correct |
| GND | GND | ground | — |
| L/R | **GND** | LOW ⇒ mic drives the **LEFT** channel | ✅ matches `I2S_CHANNEL_FMT_ONLY_LEFT` |

None of GPIO 4/5/6 touches the Octal PSRAM (35–37), the flash bus (26–32), the strapping pins
(0/3/45/46), USB (19/20), UART0 (43/44), or the non-existent 22–25. All three are in the
documented free set (1, 2, 4–18, 21, 38–42).

This map is **identical to the prior build's wiring**, which means that build's I²S evidence
(sample rate, bit alignment, noise spectrum) applies to the same electrical configuration —
though it still requires re-measurement here before being quoted.

### ⚠ Serial interface — corrected by measurement, 2026-09-09

**This board enumerates through a CH343 USB-UART bridge, not the ESP32-S3's native
USB-Serial/JTAG.** Measured directly during bring-up:

| Observation | Evidence |
|---|---|
| Port present | **COM8**, "USB-Enhanced-SERIAL CH343" |
| Native USB-Serial/JTAG (`VID_303A`) | **not enumerated** |
| ROM bootloader on COM8 @ 115200 | ✅ clean (`ESP-ROM:esp32s3-20210327`, `SPI_FAST_FLASH_BOOT`) |
| Sketch `Serial` output with `ARDUINO_USB_CDC_ON_BOOT=1` | ❌ **never arrived** — bound to the unconnected native USB CDC |
| Fix | **`ARDUINO_USB_CDC_ON_BOOT=0`** ⇒ `Serial` binds to UART0 (GPIO 43/44) → CH343 → host |

Recorded in `firmware/platformio.ini` with the reasoning. **The earlier COM5/COM7 +
`VID:PID 303A:1001` records elsewhere in this document describe a different physical
connection** and must not be used to configure a build.

## 5. Audio front-end facts to re-verify

| Fact | Prior value | Why it matters |
|---|---|---|
| Actual sample rate | 16,001.60 Hz (+0.010 %) | Feature timing; must be measured, not assumed |
| Bit alignment | 24-bit left-justified in 32-bit slot; keep the upper 16 bits | Wrong shift ⇒ silent 48 dB level error |
| Noise spectrum | 64.6 % of energy < 100 Hz | Justifies band-limited VAD and the 125 Hz mel floor |
| Clipping | 0 clipped samples observed | Level headroom |

All rows are **[prior-build]** and are re-measured in Phase A of `BUILD_PLAN.md`.

## 6. Development host

| Item | Value | Source |
|---|---|---|
| OS | Windows 11 Pro 10.0.26200 | [measured-here] |
| CPU | Intel Core i3-8100, 4C/4T @ 3.60 GHz | [measured-here] |
| RAM | 15.9 GB | [measured-here] |
| GPU | Intel UHD 630 — **no CUDA. All training is CPU-only.** | [measured-here] |
| Disk C: | 128 GB NVMe SSD, **12.84 GB free (10.85 %)** after the 2026-09-09 cache cleanup that recovered 12.36 GB; it was at 0 bytes | [measured-here] `STORAGE_AUDIT.md` |
| Disk D: / E: | 1 TB SATA HDD → 337 GB / 446 GB free | [measured-here] |
| Ethernet | UP, **192.168.1.2/24**, gateway **192.168.1.1 reachable**, internet reachable | [measured-here] |
| Wi-Fi | Realtek RTL8821CE — radio types **802.11 b/g/n** (2.4 GHz) **+ a/ac** (5 GHz); radio hardware+software ON but **DISCONNECTED**. `Hosted network supported: No` (legacy SoftAP unavailable; Mobile Hotspot uses WiFi-Direct and is untested) | [measured-here] `netsh wlan show drivers` |
| **ESP32 attached?** | ✅ **YES, since 2026-09-09** — `USB\VID_303A&PID_1001` enumerated as USB Composite Device + USB Serial Device (**COM7**) + USB JTAG/serial debug unit, all `Status: OK`. Confirmed independently by `pio device list`. | **[measured-here]** |

### Networking implication for the demo

The ESP32 must reach the ASR/dashboard server over **Wi-Fi**. The host currently has its only
live link on **Ethernet (192.168.1.2)**, implying a router at `192.168.1.1`. Two workable paths:

1. **Preferred:** ESP32 joins that router's 2.4 GHz SSID and connects to `192.168.1.2`.
   Requires the SSID + password (**blocker, see `STATUS.md`**). The ESP32-S3 is **2.4 GHz only**.
2. Fallback: Windows Mobile Hotspot on the host; the server then binds the hotspot interface.

## 7. Toolchain installed on this host

| Component | Version | Source |
|---|---|---|
| PlatformIO Core | 6.1.19 | [measured-here] |
| Platform | `espressif32 @ 7.1.1` (platformio/platform-espressif32) | [measured-here] `platform.json` |
| Framework | `framework-arduinoespressif32 3.20017` = **Arduino core 2.0.17** | [measured-here] `package.json` |
| Underlying ESP-IDF | **4.4** (`ESP_IDF_VERSION_MAJOR 4 / MINOR 4`) | [measured-here] `esp_idf_version.h` |
| Toolchains present | `toolchain-xtensa-esp32s3`, `-esp32`, `toolchain-riscv32-esp` | [measured-here] |
| I²S API | **legacy `driver/i2s.h` only** — `driver/i2s_std.h` does not exist in IDF 4.4 | [prior-build] |
| Python | 3.13.9 has TensorFlow **2.20.0** + torch 2.8.0+cpu; 3.14.0 has numpy/scipy/sklearn/matplotlib | [measured-here] |

See `DECISIONS.md` **D-003** for why this Arduino/IDF-4.4 stack is kept for Phase 1 rather
than migrating to ESP-IDF 5.x.
