#!/usr/bin/env python3
"""Host-side capture tool for the INMP441 recorder firmware.

Talks to firmware/src/main.cpp over the ESP32-S3's native USB CDC link, captures
framed PCM16 blocks, verifies block continuity, and writes a WAV plus a metadata
sidecar that the dataset factory can consume directly.

    python tools/record_session.py --verify
    python tools/record_session.py --info
    python tools/record_session.py --test          # bit-alignment (STEP 5)
    python tools/record_session.py --rate 3000     # measured sample rate
    python tools/record_session.py --record silence --duration 5000 \
        --speaker SPK001 --session S001 --distance 1.0 --volume normal

Requires pyserial. It ships with PlatformIO:
    ~/.platformio/penv/Scripts/python -m pip show pyserial
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import RECORDINGS_ROOT, UPLOAD_PORT  # noqa: E402

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("ERROR: pyserial not installed.\n"
             "  pip install pyserial\n"
             "  (or use PlatformIO's python, which bundles it)")

MAGIC = b"SIH1"
HDR = 12                     # magic(4) + seq(4) + nsamp(2) + flags(2)
FLAG_DMA_OVERRUN = 0x0001
FLAG_LAST_BLOCK = 0x0004
# Known USB interfaces for this board. Measured 2026-09-09: this unit enumerates
# through a CH343 UART bridge (QinHeng, VID 1A86), NOT the ESP32-S3's native
# USB-Serial/JTAG. Both are accepted so the tool works on either wiring.
KNOWN_VIDPID = {
    (0x303A, 0x1001): "ESP32-S3 native USB-Serial/JTAG",
    (0x1A86, 0x55D3): "CH343 USB-UART bridge",
    (0x1A86, 0x7523): "CH340 USB-UART bridge",
}
KNOWN_VIDS = {0x303A, 0x1A86}
SAMPLE_RATE = 16000


# --------------------------------------------------------------------------
# link
# --------------------------------------------------------------------------
def find_port(explicit: str | None) -> str:
    if explicit:
        return explicit
    if UPLOAD_PORT:
        return UPLOAD_PORT
    cands = [p for p in list_ports.comports() if p.vid in KNOWN_VIDS]
    if len(cands) == 1:
        desc = KNOWN_VIDPID.get((cands[0].vid, cands[0].pid), "known USB bridge")
        print(f"auto-detected {cands[0].device}  ({desc})")
        return cands[0].device
    if len(cands) > 1:
        sys.exit("ERROR: multiple candidate boards; pass --port explicitly.\n  " +
                 "\n  ".join(f"{p.device} ({p.description})" for p in cands))
    ports = [f"{p.device} ({p.description})" for p in list_ports.comports()]
    sys.exit("ERROR: no board found (looked for VID 303A native USB, or 1A86 CH34x bridge).\n"
             f"  ports seen: {ports or 'none'}\n"
             "  Plug the board in, or pass --port, or set SIH_UPLOAD_PORT in .env")


def open_link(port: str, timeout: float = 2.0) -> serial.Serial:
    ser = serial.Serial(port, 921600, timeout=timeout)
    time.sleep(0.3)
    ser.reset_input_buffer()
    return ser


def send(ser: serial.Serial, cmd: str) -> None:
    ser.write((cmd + "\n").encode())
    ser.flush()


def read_text_block(ser: serial.Serial, end: str = "=== END ===",
                    timeout: float = 15.0) -> str:
    """Read ASCII lines until the firmware's end marker."""
    out, deadline = [], time.time() + timeout
    while time.time() < deadline:
        line = ser.readline().decode(errors="replace").rstrip("\r\n")
        if not line:
            continue
        out.append(line)
        if end in line:
            break
    return "\n".join(out)


def parse_kv(text: str) -> dict[str, str]:
    kv = {}
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and not line.startswith("==="):
            kv[parts[0]] = parts[1].strip()
    return kv


# --------------------------------------------------------------------------
# recording
# --------------------------------------------------------------------------
def record(ser: serial.Serial, duration_ms: int) -> tuple[bytearray, dict]:
    """Capture one recording. Returns (pcm16 bytes, capture stats)."""
    ser.reset_input_buffer()
    send(ser, f"REC {duration_ms}")

    # wait for REC_BEGIN
    deadline = time.time() + 10
    while time.time() < deadline:
        line = ser.readline().decode(errors="replace").strip()
        if line.startswith("REC_BEGIN"):
            break
        if line.startswith("ERROR"):
            raise RuntimeError(f"firmware refused: {line}")
    else:
        raise RuntimeError("timed out waiting for REC_BEGIN")

    pcm = bytearray()
    expected_seq = 0
    stats = {"blocks": 0, "seq_gaps": 0, "lost_blocks": 0,
             "overrun_blocks": 0, "resyncs": 0}

    ser.timeout = 3.0
    buf = bytearray()
    done = False
    stop_at = time.time() + duration_ms / 1000.0 + 15

    while not done and time.time() < stop_at:
        chunk = ser.read(4096)
        if not chunk:
            break
        buf += chunk
        while True:
            idx = buf.find(MAGIC)
            if idx < 0:
                if len(buf) > 8:
                    del buf[:-3]            # keep a possible partial magic
                break
            if idx > 0:
                stats["resyncs"] += 1
                del buf[:idx]
            if len(buf) < HDR:
                break
            seq, nsamp, flags = struct.unpack_from("<IHH", buf, 4)
            need = HDR + nsamp * 2
            if len(buf) < need:
                break
            payload = bytes(buf[HDR:need])
            del buf[:need]

            if seq != expected_seq:
                gap = seq - expected_seq
                if gap > 0:
                    stats["seq_gaps"] += 1
                    stats["lost_blocks"] += gap
            expected_seq = seq + 1
            if flags & FLAG_DMA_OVERRUN:
                stats["overrun_blocks"] += 1
            pcm += payload
            stats["blocks"] += 1
            if flags & FLAG_LAST_BLOCK:
                done = True
                break

    # trailing REC_END summary
    tail, deadline = [], time.time() + 5
    while time.time() < deadline:
        line = ser.readline().decode(errors="replace").strip()
        if not line:
            continue
        tail.append(line)
        if line.startswith("REC_END"):
            break
    for line in tail:
        if line.startswith("REC_END"):
            for tok in line.split()[1:]:
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    stats[f"device_{k}"] = v
    stats["samples"] = len(pcm) // 2
    return pcm, stats


# Speech-band peak that separates the session that worked from the one that
# did not: S_PILOT measured -25.3 dB median (14/17 usable), S_PILOT_03
# measured -34.2 dB (3/15 usable). -30 dB sits between them.
LEVEL_TARGET_DB = -30.0


def speech_check(pcm: bytes) -> dict:
    """Would the DATASET FACTORY accept this take?

    Transport integrity ("80000/80000 samples, 0 lost") says nothing about
    whether the microphone heard a voice. 30 takes were once recorded back to
    back and every one reported [ok] while containing only room tone - the
    speech-band level was -44.7 dBFS against a known silence floor of -44.6.

    A second, subtler failure followed: a laxer "SNR >= 10 dB" rule here passed
    11 of 15 takes that the factory then rejected 12 of, because the speech band
    sat 9 dB quieter than the session that worked. Two different definitions of
    "usable" meant the operator got told "ok" and lost the session anyway.

    So this asks the factory itself, using the factory's own span rule and
    bounds. There is one definition of usable, and the microphone stand-in for
    it lives here.

    Returns a dict; `usable` is the verdict, `reason` is what to change.
    """
    out = {"usable": None, "reason": "not checked", "band_dbfs": float("nan"),
           "band_peak_db": float("nan"), "snr_db": float("nan"),
           "span_ms": float("nan"), "truncated": False}
    try:
        import numpy as np
        from scipy import signal
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from tools.dataset_factory.audio import (_speech_envelope_db, extract_keyword,
                                                 speech_span_ms)
        from tools.dataset_factory.config import (CLIP_SAMPLES, MAX_KEYWORD_MS,
                                                  MIN_KEYWORD_MS)
    except ImportError:
        out["reason"] = "numpy/scipy unavailable - cannot check"
        out["usable"] = True                      # cannot check; do not block
        return out

    x = np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32768.0
    if x.size < 3200:
        out.update(usable=False, reason="take too short to assess")
        return out

    sos = signal.butter(4, [300 / 8000, 3400 / 8000], btype="band", output="sos")
    b = signal.sosfilt(sos, x)
    out["band_dbfs"] = float(20 * np.log10(np.sqrt((b ** 2).mean()) + 1e-12))

    edb = _speech_envelope_db(x, SAMPLE_RATE)
    if edb.size == 0:
        out.update(usable=False, reason="take too short to assess")
        return out
    floor = float(np.percentile(edb, 20))
    peak = float(edb.max())
    out["band_peak_db"], out["snr_db"] = peak, peak - floor
    out["span_ms"] = float(speech_span_ms(x, SAMPLE_RATE))

    # Did the word run off the end of the window? Four takes in S_PILOT_03 did:
    # speech was still above threshold in the final 10 ms frame.
    thr = floor + max(8.0, (peak - floor) * 0.35)
    over = np.flatnonzero(edb > thr)
    if over.size:
        out["truncated"] = bool((edb.size - 1 - over[-1]) * 0.010 < 0.10)

    # THE VERDICT IS THE FACTORY'S, NOT A SECOND OPINION.
    # Ask the real acceptance rule: a span inside the keyword duration bounds,
    # and an extracted segment that fits the 1 s window with its margins. Being
    # stricter here is not "safe" - it sends the operator away to re-record
    # takes that were fine. Level and truncation are ADVICE layered on top.
    seg = extract_keyword(x.astype(np.float32), SAMPLE_RATE)
    fits = seg is not None and seg.size <= CLIP_SAMPLES - 2 * int(SAMPLE_RATE * 0.060)
    in_range = MIN_KEYWORD_MS <= out["span_ms"] <= MAX_KEYWORD_MS
    out["usable"] = bool(in_range and fits)

    if out["usable"]:
        out["reason"] = "usable"
        if peak < LEVEL_TARGET_DB:                    # advisory, not a rejection
            out["reason"] = (f"usable but quiet ({peak:.0f} dB, prefer "
                             f"> {LEVEL_TARGET_DB:.0f}) - consider moving closer")
    elif out["snr_db"] < 6.0:
        out["reason"] = "NO SPEECH - room tone only"
    elif out["truncated"]:
        out["reason"] = "CUT OFF at the end - speak sooner after the countdown"
    elif peak < LEVEL_TARGET_DB:
        # The dominant failure in S_PILOT_02/03: at ~12 dB above the noise floor
        # only the loudest syllable clears the span threshold, so one word
        # measures as a 140 ms fragment. The cure is level, not enunciation.
        out["reason"] = (f"TOO QUIET ({peak:.0f} dB, want > {LEVEL_TARGET_DB:.0f}) "
                         f"- move closer to the mic")
    elif out["span_ms"] < MIN_KEYWORD_MS:
        out["reason"] = (f"word too short/broken ({out['span_ms']:.0f} ms, want "
                         f"{MIN_KEYWORD_MS}-{MAX_KEYWORD_MS}) - say it fully")
    elif out["span_ms"] > MAX_KEYWORD_MS:
        out["reason"] = f"word too long ({out['span_ms']:.0f} ms) - one word only"
    else:
        out["reason"] = "does not fit the 1 s window"
    return out


def write_wav(path: Path, pcm: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port")
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--test", action="store_true", help="bit-alignment analysis")
    ap.add_argument("--rate", type=int, nargs="?", const=3000, metavar="MS")
    ap.add_argument("--verify", action="store_true", help="INFO + TEST + RATE")
    ap.add_argument("--record", metavar="LABEL")
    ap.add_argument("--duration", type=int, default=3000, help="ms (default 3000)")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--speaker", default="PILOT")
    ap.add_argument("--session", default=None)
    ap.add_argument("--distance", default="1.0")
    ap.add_argument("--orientation", default="0")
    ap.add_argument("--volume", default="normal")
    ap.add_argument("--rate-label", default="normal", dest="rate_label")
    ap.add_argument("--environment", default="E1")
    ap.add_argument("--notes", default="")
    ap.add_argument("--no-prompt", action="store_true",
                    help="skip the 3-2-1 countdown (for ambient/unattended capture)")
    ap.add_argument("--expect-speech", action="store_true", default=None,
                    help="fail a take that contains no speech (default: on unless "
                         "the label looks like silence/ambient)")
    args = ap.parse_args()

    port = find_port(args.port)
    print(f"port: {port}")
    ser = open_link(port)

    # drain the boot banner
    time.sleep(0.5)
    ser.reset_input_buffer()

    if args.info or args.verify:
        send(ser, "INFO")
        print(read_text_block(ser))
        print()
    if args.test or args.verify:
        send(ser, "TEST")
        print(read_text_block(ser, timeout=25))
        print()
    if args.rate is not None or args.verify:
        ms = args.rate if args.rate is not None else 3000
        send(ser, f"RATE {ms}")
        print(read_text_block(ser, timeout=ms / 1000 + 20))
        print()

    if not args.record:
        ser.close()
        return 0

    # Ambient/silence captures legitimately contain no speech.
    if args.expect_speech is None:
        args.expect_speech = not any(t in args.record.lower()
                                     for t in ("silence", "ambient", "noise", "roomtone"))
    if not args.expect_speech:
        args.no_prompt = True
    n_no_speech = 0

    session = args.session or datetime.now().strftime("S%Y%m%d_%H%M%S")
    outdir = RECORDINGS_ROOT / args.speaker / session
    started = datetime.now(timezone.utc).isoformat()

    rc = 0
    for i in range(1, args.repeat + 1):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = f"{args.speaker}_{session}_{args.record}_{i:03d}_{stamp}"
        if not args.no_prompt:
            print(f"\n[{i}/{args.repeat}] get ready...", end="", flush=True)
            for c in (3, 2, 1):
                print(f" {c}", end="", flush=True)
                time.sleep(0.7)
            print("  >>> SPEAK NOW <<<", flush=True)
        else:
            print(f"[{i}/{args.repeat}] recording {args.duration} ms -> {base}.wav")
        try:
            pcm, stats = record(ser, args.duration)
        except RuntimeError as exc:
            print(f"  FAILED: {exc}")
            rc = 1
            continue

        wav_path = outdir / f"{base}.wav"
        write_wav(wav_path, bytes(pcm))

        expected = int(SAMPLE_RATE * args.duration / 1000)
        meta = {
            "schema_version": "1.0",
            "clip_basename": base,
            "label_hint": args.record,
            "speaker_id": args.speaker,
            "session_id": session,
            "recorded_utc": started,
            "device": {"id": "H1", "type": "inmp441_esp32s3", "port": port},
            "audio": {"sample_rate_hz": SAMPLE_RATE, "bit_depth": 16, "channels": 1,
                      "requested_ms": args.duration,
                      "samples_expected": expected,
                      "samples_captured": stats.get("samples", 0)},
            "conditions": {"distance_m": args.distance,
                           "orientation_deg": args.orientation,
                           "volume": args.volume, "rate": args.rate_label,
                           "environment_id": args.environment},
            "capture_stats": stats,
            "notes": args.notes,
        }
        (outdir / f"{base}.json").write_text(json.dumps(meta, indent=2) + "\n",
                                             encoding="utf-8")

        got, exp = stats.get("samples", 0), expected
        drift = 100.0 * (got - exp) / exp if exp else 0.0
        chk = speech_check(bytes(pcm))
        meta["capture_stats"].update({
            "speech_band_dbfs": None if chk["band_dbfs"] != chk["band_dbfs"] else round(chk["band_dbfs"], 1),
            "speech_band_peak_db": None if chk["band_peak_db"] != chk["band_peak_db"] else round(chk["band_peak_db"], 1),
            "speech_band_snr_db": None if chk["snr_db"] != chk["snr_db"] else round(chk["snr_db"], 1),
            "keyword_span_ms": None if chk["span_ms"] != chk["span_ms"] else round(chk["span_ms"]),
            "truncated": chk["truncated"],
            "factory_usable": chk["usable"],
            "verdict": chk["reason"],
        })
        (outdir / f"{base}.json").write_text(
            json.dumps(meta, indent=2) + "\n", encoding="utf-8")

        flag = "ok"
        if stats["lost_blocks"] or stats["overrun_blocks"]:
            flag = "DROPOUTS"
            rc = 1
        elif abs(drift) > 1.0:
            flag = "LENGTH"
            rc = 1
        elif args.expect_speech and not chk["usable"]:
            flag = chk["reason"]
            rc = 1
            n_no_speech += 1
        print(f"  {got}/{exp} samples ({drift:+.2f}%)  lost={stats['lost_blocks']} "
              f"overrun={stats['overrun_blocks']}  "
              f"peak={chk['band_peak_db']:.0f} dB  span={chk['span_ms']:.0f} ms  [{flag}]")
        if flag not in ("ok", "DROPOUTS", "LENGTH"):
            print(f"        ^ REJECTED: {chk['reason']}. Re-record this take.")

    ser.close()
    print(f"\nwrote to {outdir}")
    print("next: python tools/audio_qc.py " + str(outdir))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
