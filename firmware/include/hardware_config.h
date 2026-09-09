// hardware_config.h — THE single authoritative hardware definition.
//
// Every pin, every audio parameter, one place. Nothing else in this project may
// define a GPIO number. If a value is wrong it is wrong here, once.
//
// Board : ESP32-S3-WROOM-1-N16R8 (16 MB quad flash, 8 MB octal PSRAM, 2x LX7 @ 240 MHz)
// Mic   : INMP441 I2S MEMS, 24-bit, 64 SCK per WS frame
//
// PIN MAP: supplied by the user as the verified physical wiring, 2026-09-09.
// Validated against the module's reserved-GPIO table (HARDWARE.md 3):
//   GPIO 4, 5, 6 are NOT PSRAM (35-37), NOT flash (26-32), NOT strapping
//   (0/3/45/46), NOT USB (19/20), NOT UART0 (43/44), and all lie in the
//   documented free set (1, 2, 4-18, 21, 38-42).  NO CONFLICT.

#pragma once

#include <stdint.h>

// ---------------------------------------------------------------------------
// INMP441 <-> ESP32-S3 wiring  (VERIFIED PHYSICAL MAP - do not change)
// ---------------------------------------------------------------------------
//   INMP441            ESP32-S3
//   ---------------------------------------------------------------
//   SCK   ...........  GPIO 6    bit clock    (ESP32 -> mic)
//   WS    ...........  GPIO 5    word select  (ESP32 -> mic)
//   SD    ...........  GPIO 4    audio data   (mic -> ESP32)
//   VDD   ...........  3V3       1.8-3.3 V part. NEVER 5 V (abs max 3.63 V)
//   GND   ...........  GND
//   L/R   ...........  GND       LOW => mic drives the LEFT channel
// ---------------------------------------------------------------------------

#define PIN_I2S_SCK   6   // BCLK
#define PIN_I2S_WS    5   // LRCLK / word select
#define PIN_I2S_SD    4   // SDATA in (mic -> MCU)

// L/R is hard-wired to GND, so the microphone transmits only during the LEFT
// (WS low) phase. The I2S channel format below must match this.
#define INMP441_CHANNEL_IS_LEFT 1

// ---------------------------------------------------------------------------
// Audio format  (fixed by ARCHITECTURE.md 3 / KWS_ENGINE_DECISION.md 4)
// ---------------------------------------------------------------------------
#define AUDIO_SAMPLE_RATE_HZ  16000   // no resampling anywhere in the project
#define AUDIO_CHANNELS        1       // mono, LEFT only
#define AUDIO_BITS_OUT        16      // signed PCM16 little-endian on the wire

// The INMP441 emits 24-bit two's-complement data, MSB first, left-justified in
// a 32-bit I2S slot => the sample occupies bits 31..8 and bits 7..0 are unused.
//
//   raw32 >> 8   -> 24-bit signed
//   raw32 >> 16  -> 16-bit signed   <-- what we transmit
//
// THIS IS NOT ASSUMED. The `TEST` command measures which bit positions are ever
// set across thousands of real samples and reports the shift the hardware
// actually requires. Change this only to a value that command justifies.
#ifndef I2S_SHIFT_BITS
#define I2S_SHIFT_BITS 16
#endif

// ---------------------------------------------------------------------------
// I2S peripheral / DMA
// ---------------------------------------------------------------------------
#define I2S_PORT_NUM        0     // I2S_NUM_0
#define I2S_BITS_PER_SLOT   32    // read 32-bit slots, shift down in software
#define I2S_DMA_BUF_COUNT   8     // 8 x 256 samples = 2048 samples = 128 ms
#define I2S_DMA_BUF_LEN     256   // samples per DMA buffer
#define I2S_READ_CHUNK      512   // samples per read / per transmitted block

// ---------------------------------------------------------------------------
// Host link
// ---------------------------------------------------------------------------
// Native USB-Serial/JTAG (VID:PID 303A:1001). The baud rate is nominal over
// USB CDC; the link sustains far more than the 32 kB/s this recorder needs
// (16000 samples/s x 2 bytes).
#define LINK_BAUD 921600

// Binary block framing. The host uses `seq` to detect dropped blocks.
//   'S','I','H','1' | seq u32 | nsamp u16 | flags u16 | int16 payload
#define BLOCK_MAGIC_0 'S'
#define BLOCK_MAGIC_1 'I'
#define BLOCK_MAGIC_2 'H'
#define BLOCK_MAGIC_3 '1'

#define FLAG_DMA_OVERRUN  0x0001  // i2s_read timed out or returned short
#define FLAG_FIRST_BLOCK  0x0002
#define FLAG_LAST_BLOCK   0x0004

#define FW_RECORDER_VERSION "1.0.0"
