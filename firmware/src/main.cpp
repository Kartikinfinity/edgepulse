// main.cpp — INMP441 audio capture recorder for dataset collection.
//
// SCOPE: hardware bring-up and dataset capture ONLY. No ML, no Wi-Fi, no UI.
// This firmware exists to prove the audio path is real and to feed the dataset
// factory. It deliberately does nothing else.
//
// Commands (newline-terminated ASCII on the USB CDC serial link):
//
//   INFO          chip / PSRAM / heap / pin map / I2S configuration
//   TEST          bit-alignment analysis on raw 32-bit I2S words  (STEP 5)
//   RATE <ms>     measure the ACTUAL sample rate against esp_timer
//   REC <ms>      stream signed PCM16 in framed binary blocks
//   STOP          abort an in-progress recording
//
// Everything the host needs to detect a fault is transmitted: per-block
// sequence numbers, an overrun flag, and an end-of-recording summary.

#include <Arduino.h>
#include <string.h>

#include "driver/i2s.h"     // legacy I2S API - the only one present in IDF 4.4
#include "esp_timer.h"
#include "esp_chip_info.h"
#include "esp_flash.h"

#include "hardware_config.h"

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
static int32_t  g_raw[I2S_READ_CHUNK];    // raw 32-bit I2S slots
static int16_t  g_pcm[I2S_READ_CHUNK];    // converted signed PCM16
static bool     g_i2s_ready = false;

// Statistics for the current recording
static uint32_t g_seq            = 0;
static uint32_t g_overruns       = 0;
static uint32_t g_short_reads    = 0;
static uint64_t g_samples_total  = 0;
static int64_t  g_t_start_us     = 0;

// ---------------------------------------------------------------------------
// I2S bring-up
// ---------------------------------------------------------------------------
static bool i2sInit() {
  i2s_config_t cfg = {};
  cfg.mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  cfg.sample_rate          = AUDIO_SAMPLE_RATE_HZ;
  cfg.bits_per_sample      = I2S_BITS_PER_SAMPLE_32BIT;   // read full 32-bit slots
#if INMP441_CHANNEL_IS_LEFT
  cfg.channel_format       = I2S_CHANNEL_FMT_ONLY_LEFT;   // L/R tied to GND
#else
  cfg.channel_format       = I2S_CHANNEL_FMT_ONLY_RIGHT;
#endif
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;   // Philips, 1-bit delay
  cfg.intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count        = I2S_DMA_BUF_COUNT;
  cfg.dma_buf_len          = I2S_DMA_BUF_LEN;
  cfg.use_apll             = false;
  cfg.tx_desc_auto_clear   = false;
  cfg.fixed_mclk           = 0;

  if (i2s_driver_install((i2s_port_t)I2S_PORT_NUM, &cfg, 0, NULL) != ESP_OK) return false;

  i2s_pin_config_t pins = {};
  pins.mck_io_num   = I2S_PIN_NO_CHANGE;
  pins.bck_io_num   = PIN_I2S_SCK;
  pins.ws_io_num    = PIN_I2S_WS;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num  = PIN_I2S_SD;

  if (i2s_set_pin((i2s_port_t)I2S_PORT_NUM, &pins) != ESP_OK) return false;

  i2s_zero_dma_buffer((i2s_port_t)I2S_PORT_NUM);
  return true;
}

// Read one chunk of raw 32-bit slots. Returns samples actually read.
static size_t readRaw(int32_t *dst, size_t want, bool *overrun) {
  size_t bytes = 0;
  esp_err_t err = i2s_read((i2s_port_t)I2S_PORT_NUM, dst,
                           want * sizeof(int32_t), &bytes,
                           pdMS_TO_TICKS(200));
  size_t got = bytes / sizeof(int32_t);
  *overrun = (err != ESP_OK) || (got != want);
  return got;
}

// ---------------------------------------------------------------------------
// INFO
// ---------------------------------------------------------------------------
static void cmdInfo() {
  esp_chip_info_t chip;
  esp_chip_info(&chip);
  uint32_t flash_sz = 0;
  esp_flash_get_size(NULL, &flash_sz);

  Serial.println(F("=== INFO ==="));
  Serial.printf("fw_version       %s\n", FW_RECORDER_VERSION);
  Serial.printf("chip_model       %d  revision %d\n", (int)chip.model, (int)chip.revision);
  Serial.printf("chip_cores       %d\n", (int)chip.cores);
  Serial.printf("cpu_freq_mhz     %u\n", (unsigned)getCpuFrequencyMhz());
  Serial.printf("flash_bytes      %u\n", (unsigned)flash_sz);
  Serial.printf("psram_found      %d\n", (int)psramFound());
  Serial.printf("psram_bytes      %u\n", (unsigned)ESP.getPsramSize());
  Serial.printf("heap_total       %u\n", (unsigned)ESP.getHeapSize());
  Serial.printf("heap_free        %u\n", (unsigned)ESP.getFreeHeap());
  Serial.println(F("--- pin map (hardware_config.h) ---"));
  Serial.printf("i2s_sck_bclk     GPIO %d\n", PIN_I2S_SCK);
  Serial.printf("i2s_ws_lrclk     GPIO %d\n", PIN_I2S_WS);
  Serial.printf("i2s_sd_data_in   GPIO %d\n", PIN_I2S_SD);
  Serial.printf("channel          %s\n", INMP441_CHANNEL_IS_LEFT ? "LEFT (L/R=GND)" : "RIGHT");
  Serial.println(F("--- audio ---"));
  Serial.printf("sample_rate_hz   %d\n", AUDIO_SAMPLE_RATE_HZ);
  Serial.printf("channels         %d\n", AUDIO_CHANNELS);
  Serial.printf("bits_out         %d\n", AUDIO_BITS_OUT);
  Serial.printf("i2s_slot_bits    %d\n", I2S_BITS_PER_SLOT);
  Serial.printf("i2s_shift_bits   %d\n", I2S_SHIFT_BITS);
  Serial.printf("dma_buf_count    %d\n", I2S_DMA_BUF_COUNT);
  Serial.printf("dma_buf_len      %d\n", I2S_DMA_BUF_LEN);
  Serial.printf("i2s_ready        %d\n", (int)g_i2s_ready);
  Serial.println(F("=== END ==="));
}

// ---------------------------------------------------------------------------
// TEST — bit-alignment verification (STEP 5)
//
// Does NOT assume the shift. Accumulates, over many real samples:
//   or_all   : every bit position ever SET
//   and_all  : every bit position ALWAYS set
//   low8_nz  : how many samples have any of bits 7..0 set
// For an INMP441 emitting 24 bits left-justified in a 32-bit slot, bits 7..0
// must NEVER be set. That single observation proves the alignment.
// ---------------------------------------------------------------------------
static void cmdTest() {
  const int CHUNKS = 40;                       // 40 x 512 = 20480 samples ~1.3 s
  uint32_t or_all = 0, and_all = 0xFFFFFFFFu;
  uint32_t low8_nz = 0, low16_nz = 0;
  int32_t  vmin = INT32_MAX, vmax = INT32_MIN;
  uint64_t n = 0;
  uint32_t overruns = 0;

  Serial.println(F("=== TEST ==="));
  if (!g_i2s_ready) { Serial.println(F("ERROR i2s_not_ready")); Serial.println(F("=== END ===")); return; }

  // discard the first chunk: the mic needs ~50 ms after clocks start
  bool ov = false;
  readRaw(g_raw, I2S_READ_CHUNK, &ov);
  delay(60);

  for (int c = 0; c < CHUNKS; ++c) {
    size_t got = readRaw(g_raw, I2S_READ_CHUNK, &ov);
    if (ov) overruns++;
    for (size_t i = 0; i < got; ++i) {
      uint32_t u = (uint32_t)g_raw[i];
      or_all  |= u;
      and_all &= u;
      if (u & 0x000000FFu) low8_nz++;
      if (u & 0x0000FFFFu) low16_nz++;
      if (g_raw[i] < vmin) vmin = g_raw[i];
      if (g_raw[i] > vmax) vmax = g_raw[i];
      n++;
    }
  }

  // Highest and lowest bit positions ever set
  int hi = -1, lo = -1;
  for (int b = 31; b >= 0; --b) if (or_all & (1u << b)) { hi = b; break; }
  for (int b = 0; b < 32; ++b)  if (or_all & (1u << b)) { lo = b; break; }

  Serial.printf("samples          %llu\n", (unsigned long long)n);
  Serial.printf("overrun_chunks   %u\n", (unsigned)overruns);
  Serial.printf("or_all           0x%08X\n", (unsigned)or_all);
  Serial.printf("and_all          0x%08X\n", (unsigned)and_all);
  Serial.printf("highest_bit_set  %d\n", hi);
  Serial.printf("lowest_bit_set   %d\n", lo);
  Serial.printf("low8_nonzero     %u\n", (unsigned)low8_nz);
  Serial.printf("low16_nonzero    %u\n", (unsigned)low16_nz);
  Serial.printf("raw_min          %ld\n", (long)vmin);
  Serial.printf("raw_max          %ld\n", (long)vmax);

  // Interpretation, computed on-device so it cannot be misremembered later.
  if (n == 0) {
    Serial.println(F("verdict          NO_DATA - check wiring/power"));
  } else if (or_all == 0) {
    Serial.println(F("verdict          ALL_ZERO - mic silent or SD not connected"));
  } else if (low8_nz == 0) {
    Serial.println(F("verdict          24_IN_32_LEFT_JUSTIFIED (bits 7..0 never set)"));
    Serial.printf ("recommended_shift %d   (raw>>16 => PCM16)\n", 16);
  } else if (low16_nz == 0) {
    Serial.println(F("verdict          16_IN_32 (bits 15..0 never set)"));
    Serial.printf ("recommended_shift %d\n", 16);
  } else {
    Serial.println(F("verdict          UNEXPECTED - low bits are active; do NOT assume >>16"));
    Serial.printf ("recommended_shift %d   (derived from highest_bit_set)\n",
                   (hi >= 15) ? (hi - 15) : 0);
  }
  Serial.println(F("=== END ==="));
}

// ---------------------------------------------------------------------------
// RATE — measure the ACTUAL sample rate against esp_timer
// ---------------------------------------------------------------------------
static void cmdRate(uint32_t ms) {
  if (ms < 500) ms = 500;
  Serial.println(F("=== RATE ==="));
  if (!g_i2s_ready) { Serial.println(F("ERROR i2s_not_ready")); Serial.println(F("=== END ===")); return; }

  bool ov = false;
  readRaw(g_raw, I2S_READ_CHUNK, &ov);   // discard priming chunk
  delay(60);
  i2s_zero_dma_buffer((i2s_port_t)I2S_PORT_NUM);

  // CRITICAL: drain the DMA ring before timing. It holds
  // I2S_DMA_BUF_COUNT * I2S_DMA_BUF_LEN samples that were captured BEFORE t0.
  // They read back instantly and inflate the computed rate - measured as a
  // spurious +2.0% before this drain was added. After enough chunks the reads
  // are ADC-limited, which is the steady state we want to measure.
  const int drain_chunks = (I2S_DMA_BUF_COUNT * I2S_DMA_BUF_LEN) / I2S_READ_CHUNK + 4;
  for (int i = 0; i < drain_chunks; ++i) readRaw(g_raw, I2S_READ_CHUNK, &ov);

  uint64_t n = 0;
  uint32_t overruns = 0;
  int64_t t0 = esp_timer_get_time();
  int64_t deadline = t0 + (int64_t)ms * 1000;
  while (esp_timer_get_time() < deadline) {
    size_t got = readRaw(g_raw, I2S_READ_CHUNK, &ov);
    if (ov) overruns++;
    n += got;
  }
  int64_t t1 = esp_timer_get_time();
  double elapsed_s = (double)(t1 - t0) / 1e6;
  double rate = (elapsed_s > 0) ? (double)n / elapsed_s : 0.0;

  Serial.printf("samples          %llu\n", (unsigned long long)n);
  Serial.printf("elapsed_us       %lld\n", (long long)(t1 - t0));
  Serial.printf("measured_rate_hz %.2f\n", rate);
  Serial.printf("nominal_rate_hz  %d\n", AUDIO_SAMPLE_RATE_HZ);
  Serial.printf("deviation_pct    %.4f\n",
                100.0 * (rate - AUDIO_SAMPLE_RATE_HZ) / AUDIO_SAMPLE_RATE_HZ);
  Serial.printf("overrun_chunks   %u\n", (unsigned)overruns);
  Serial.println(F("=== END ==="));
}

// ---------------------------------------------------------------------------
// REC — stream framed PCM16 blocks
// ---------------------------------------------------------------------------
static void sendBlock(const int16_t *pcm, uint16_t nsamp, uint16_t flags) {
  uint8_t hdr[12];
  hdr[0] = BLOCK_MAGIC_0; hdr[1] = BLOCK_MAGIC_1;
  hdr[2] = BLOCK_MAGIC_2; hdr[3] = BLOCK_MAGIC_3;
  memcpy(&hdr[4], &g_seq, 4);
  memcpy(&hdr[8], &nsamp, 2);
  memcpy(&hdr[10], &flags, 2);
  Serial.write(hdr, sizeof(hdr));
  Serial.write((const uint8_t *)pcm, (size_t)nsamp * sizeof(int16_t));
  g_seq++;
}

static void cmdRec(uint32_t ms) {
  if (ms == 0) ms = 3000;
  if (!g_i2s_ready) { Serial.println(F("ERROR i2s_not_ready")); return; }

  g_seq = 0; g_overruns = 0; g_short_reads = 0; g_samples_total = 0;

  // Prime: discard one chunk and let the mic settle, then clear DMA so the
  // recording starts on fresh audio rather than stale buffer contents.
  bool ov = false;
  readRaw(g_raw, I2S_READ_CHUNK, &ov);
  delay(60);
  i2s_zero_dma_buffer((i2s_port_t)I2S_PORT_NUM);
  // drain the pre-filled DMA ring so the recording starts on live audio and the
  // reported measured_rate_hz is not inflated by buffered samples (see cmdRate)
  {
    const int drain = (I2S_DMA_BUF_COUNT * I2S_DMA_BUF_LEN) / I2S_READ_CHUNK + 4;
    for (int i = 0; i < drain; ++i) readRaw(g_raw, I2S_READ_CHUNK, &ov);
  }

  const uint64_t want = (uint64_t)AUDIO_SAMPLE_RATE_HZ * ms / 1000ULL;

  Serial.printf("REC_BEGIN samples=%llu rate=%d bits=%d ch=%d shift=%d\n",
                (unsigned long long)want, AUDIO_SAMPLE_RATE_HZ,
                AUDIO_BITS_OUT, AUDIO_CHANNELS, I2S_SHIFT_BITS);
  Serial.flush();

  g_t_start_us = esp_timer_get_time();
  bool first = true;

  while (g_samples_total < want) {
    size_t got = readRaw(g_raw, I2S_READ_CHUNK, &ov);
    uint16_t flags = 0;
    if (ov)   { g_overruns++;    flags |= FLAG_DMA_OVERRUN; }
    if (first){ flags |= FLAG_FIRST_BLOCK; first = false; }
    if (got != I2S_READ_CHUNK) g_short_reads++;

    // 32-bit slot -> signed PCM16. The shift is the value TEST justified.
    for (size_t i = 0; i < got; ++i) {
      g_pcm[i] = (int16_t)(g_raw[i] >> I2S_SHIFT_BITS);
    }

    uint64_t remaining = want - g_samples_total;
    uint16_t n = (uint16_t)((got < remaining) ? got : remaining);
    if (g_samples_total + n >= want) flags |= FLAG_LAST_BLOCK;

    sendBlock(g_pcm, n, flags);
    g_samples_total += n;

    // Abort on STOP without blocking the capture loop.
    if (Serial.available()) {
      String s = Serial.readStringUntil('\n');
      s.trim();
      if (s.equalsIgnoreCase("STOP")) break;
    }
  }

  int64_t t1 = esp_timer_get_time();
  double elapsed_s = (double)(t1 - g_t_start_us) / 1e6;
  Serial.flush();
  Serial.printf("\nREC_END samples=%llu blocks=%u elapsed_us=%lld "
                "measured_rate_hz=%.2f overruns=%u short_reads=%u\n",
                (unsigned long long)g_samples_total, (unsigned)g_seq,
                (long long)(t1 - g_t_start_us),
                elapsed_s > 0 ? (double)g_samples_total / elapsed_s : 0.0,
                (unsigned)g_overruns, (unsigned)g_short_reads);
  Serial.flush();
}

// ---------------------------------------------------------------------------
// Arduino entry points
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(LINK_BAUD);
  uint32_t t0 = millis();
  while (!Serial && (millis() - t0) < 3000) { delay(10); }
  delay(200);

  Serial.println();
  Serial.println(F("============================================================"));
  Serial.printf (" SIH KWS recorder %s  -  INMP441 capture, no ML\n", FW_RECORDER_VERSION);
  Serial.printf ( " pins: SCK=GPIO%d  WS=GPIO%d  SD=GPIO%d  (L/R=GND, LEFT)\n",
                  PIN_I2S_SCK, PIN_I2S_WS, PIN_I2S_SD);
  Serial.println(F("============================================================"));

  g_i2s_ready = i2sInit();
  Serial.printf("i2s_init %s\n", g_i2s_ready ? "OK" : "FAILED");
  Serial.println(F("commands: INFO | TEST | RATE <ms> | REC <ms> | STOP"));
  Serial.println(F("READY"));
}

void loop() {
  if (!Serial.available()) { delay(5); return; }

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  int sp = line.indexOf(' ');
  String cmd = (sp < 0) ? line : line.substring(0, sp);
  uint32_t arg = (sp < 0) ? 0 : (uint32_t)line.substring(sp + 1).toInt();
  cmd.toUpperCase();

  if      (cmd == "INFO") cmdInfo();
  else if (cmd == "TEST") cmdTest();
  else if (cmd == "RATE") cmdRate(arg ? arg : 2000);
  else if (cmd == "REC")  cmdRec(arg ? arg : 3000);
  else if (cmd == "STOP") Serial.println(F("OK idle"));
  else                    Serial.printf("ERROR unknown_command '%s'\n", cmd.c_str());
}
