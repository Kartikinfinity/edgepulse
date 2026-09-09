"""Audio primitives for the dataset factory — all deterministic given a seed.

Every stochastic function takes an explicit numpy Generator so a clip can be
reproduced from its manifest row alone.
"""

from __future__ import annotations

import hashlib
import wave
from pathlib import Path

import numpy as np
from scipy import signal

from .config import (CLIP_SAMPLES, DTYPE, MASTER_SEED, MIC_HPF_HZ, MIC_LPF_HZ, SR)


# ---------------------------------------------------------------------------
# seeding
# ---------------------------------------------------------------------------
def rng_for(*parts) -> np.random.Generator:
    """Derive a reproducible Generator from a stable string key."""
    key = "|".join(str(p) for p in parts)
    h = hashlib.sha256(f"{MASTER_SEED}|{key}".encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


def seed_of(*parts) -> int:
    key = "|".join(str(p) for p in parts)
    h = hashlib.sha256(f"{MASTER_SEED}|{key}".encode()).digest()
    return int.from_bytes(h[:4], "little")


# ---------------------------------------------------------------------------
# io
# ---------------------------------------------------------------------------
def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError(f"{path}: {sw*8}-bit, expected 16")
    x = np.frombuffer(raw, dtype=DTYPE).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def write_wav(path: Path, x: np.ndarray, sr: int = SR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    y = np.clip(x, -1.0, 1.0)
    pcm = (y * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def sha256_array(x: np.ndarray) -> str:
    pcm = (np.clip(x, -1, 1) * 32767.0).astype(np.int16)
    return hashlib.sha256(pcm.tobytes()).hexdigest()


# ---------------------------------------------------------------------------
# resampling / trimming
# ---------------------------------------------------------------------------
def resample_to(x: np.ndarray, sr_in: int, sr_out: int = SR) -> np.ndarray:
    if sr_in == sr_out:
        return x.astype(np.float32)
    g = np.gcd(sr_in, sr_out)
    return signal.resample_poly(x, sr_out // g, sr_in // g).astype(np.float32)


def trim_silence(x: np.ndarray, sr: int = SR, thresh_db: float = -45.0,
                 pad_ms: float = 25.0) -> np.ndarray:
    """Trim leading/trailing silence. TTS pads heavily; untrimmed output would
    put the keyword in the wrong place and inflate its measured duration."""
    if x.size < 400:
        return x
    f = max(1, int(sr * 0.010))
    n = x.size // f
    if n < 3:
        return x
    e = (x[:n * f].reshape(n, f) ** 2).mean(axis=1)
    edb = 10 * np.log10(e + 1e-12)
    thr = max(edb.max() + thresh_db, edb.max() - 60.0)
    act = np.flatnonzero(edb > thr)
    if act.size == 0:
        return x
    pad = int(sr * pad_ms / 1000.0)
    lo = max(0, act[0] * f - pad)
    hi = min(x.size, (act[-1] + 1) * f + pad)
    return x[lo:hi]


def _speech_envelope_db(x: np.ndarray, sr: int) -> np.ndarray:
    """Frame energies in dB, computed on the SPEECH BAND only.

    Critical for real INMP441 audio: ~95% of its raw energy sits below 100 Hz
    (measured, EXP-004), so an envelope taken on the raw signal tracks rumble,
    not speech. Measuring on 300-3400 Hz is what made the EXP-005 duration
    analysis work, and skipping it here rejected 16 of 17 real recordings.
    """
    sos = signal.butter(4, [300.0 / (sr / 2), min(3400.0, sr / 2 * 0.98) / (sr / 2)],
                        btype="band", output="sos")
    y = signal.sosfilt(sos, x.astype(np.float64))
    f = max(1, int(sr * 0.010))
    n = y.size // f
    if n < 3:
        return np.zeros(0)
    e = (y[:n * f].reshape(n, f) ** 2).mean(axis=1)
    return 10 * np.log10(e + 1e-12)


def speech_span_ms(x: np.ndarray, sr: int = SR) -> float:
    """Duration of the longest contiguous speech run, gaps < 120 ms merged.
    Threshold is relative to the NOISE FLOOR, not the peak: a peak-relative
    threshold fragments one word into several runs (measured, EXP-005)."""
    if x.size < sr // 10:
        return 0.0
    edb = _speech_envelope_db(x, sr)
    if edb.size == 0:
        return 0.0
    floor = np.percentile(edb, 20)
    snr = edb.max() - floor
    thr = floor + max(8.0, snr * 0.35)
    idx = np.flatnonzero(edb > thr)
    if idx.size == 0:
        return 0.0
    runs, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > 12:          # 120 ms gap: a /k/ closure must not split it
            runs.append((s, prev))
            s = i
        prev = i
    runs.append((s, prev))
    return max((b - a + 1) * 10.0 for a, b in runs)


def speech_span_bounds(x: np.ndarray, sr: int = SR) -> tuple[int, int] | None:
    """Sample bounds of the longest speech run, same rule as speech_span_ms.

    Needed because a real 3 s recording does not fit a 1 s window: the keyword
    must be LOCATED and extracted, never randomly cropped. A random crop can
    miss the word entirely and label a keyword-free clip as positive - a real
    bug found in the first smoke build, where all 90 real positives had onset 0.
    """
    if x.size < sr // 10:
        return None
    f = max(1, int(sr * 0.010))
    edb = _speech_envelope_db(x, sr)
    if edb.size == 0:
        return None
    floor = np.percentile(edb, 20)
    snr = edb.max() - floor
    thr = floor + max(8.0, snr * 0.35)
    idx = np.flatnonzero(edb > thr)
    if idx.size == 0:
        return None
    runs, st, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > 12:
            runs.append((st, prev))
            st = i
        prev = i
    runs.append((st, prev))
    a, b = max(runs, key=lambda r: r[1] - r[0])
    return a * f, min(x.size, (b + 1) * f)


def extract_keyword(x: np.ndarray, sr: int = SR,
                    pad_ms: float = 40.0) -> np.ndarray | None:
    """Cut just the spoken word (plus a little context) out of a long recording."""
    b = speech_span_bounds(x, sr)
    if b is None:
        return None
    pad = int(sr * pad_ms / 1000.0)
    lo = max(0, b[0] - pad)
    hi = min(x.size, b[1] + pad)
    seg = x[lo:hi]
    return seg if seg.size > 0 else None


# ---------------------------------------------------------------------------
# channel / augmentation
# ---------------------------------------------------------------------------
def mic_band_limit(x: np.ndarray, sr: int = SR) -> np.ndarray:
    """Approximate the INMP441 channel: -3 dB at 60 Hz and 15 kHz. This is the
    domain-adaptation step that moves clean TTS and public audio toward the
    deployment microphone."""
    sos_hp = signal.butter(2, MIC_HPF_HZ / (sr / 2), btype="high", output="sos")
    sos_lp = signal.butter(2, min(MIC_LPF_HZ, sr / 2 * 0.98) / (sr / 2),
                           btype="low", output="sos")
    return signal.sosfilt(sos_lp, signal.sosfilt(sos_hp, x)).astype(np.float32)


def apply_gain_db(x: np.ndarray, db: float) -> np.ndarray:
    return (x * (10.0 ** (db / 20.0))).astype(np.float32)


def mix_noise(x: np.ndarray, noise: np.ndarray, snr_db: float,
              rng: np.random.Generator) -> np.ndarray:
    """Mix noise at a target SNR, tiling or cropping the noise as needed."""
    if noise.size == 0:
        return x
    if noise.size < x.size:
        reps = int(np.ceil(x.size / noise.size))
        noise = np.tile(noise, reps)
    off = int(rng.integers(0, max(1, noise.size - x.size + 1)))
    nz = noise[off:off + x.size].astype(np.float32)
    ps, pn = float((x ** 2).mean()), float((nz ** 2).mean())
    if pn <= 1e-12 or ps <= 1e-12:
        return x
    scale = np.sqrt(ps / (pn * (10.0 ** (snr_db / 10.0))))
    return (x + nz * scale).astype(np.float32)


def apply_rir(x: np.ndarray, rir: np.ndarray) -> np.ndarray:
    if rir.size == 0:
        return x
    rir = rir / (np.abs(rir).max() + 1e-9)
    y = signal.fftconvolve(x, rir)[: x.size]
    p0, p1 = float((x ** 2).mean()), float((y ** 2).mean())
    if p1 > 1e-12:
        y *= np.sqrt(p0 / p1)
    return y.astype(np.float32)


def change_speed(x: np.ndarray, factor: float) -> np.ndarray:
    """Resample-based speed change. Pitch moves with it, which is acceptable
    inside +-8%; beyond that the keyword leaves its observed duration range."""
    if abs(factor - 1.0) < 1e-3:
        return x
    n = max(1, int(round(x.size / factor)))
    return signal.resample(x, n).astype(np.float32)


def triangular(rng: np.random.Generator, lo: float, hi: float, mode: float) -> float:
    return float(rng.triangular(lo, min(max(mode, lo), hi), hi))


# ---------------------------------------------------------------------------
# window extraction
# ---------------------------------------------------------------------------
def place_in_window(word: np.ndarray, rng: np.random.Generator,
                    margin_samples: int) -> tuple[np.ndarray, int, int]:
    """Place a trimmed utterance at a random admissible offset inside a 1.0 s
    window. Offset sampling is NOT augmentation - it is the distribution the
    device actually sees, so it applies to every split."""
    out = np.zeros(CLIP_SAMPLES, dtype=np.float32)
    if word.size >= CLIP_SAMPLES:
        # Callers must extract the word first. Cropping here would destroy the
        # positional guarantee and could produce a keyword-free "positive".
        start = int(rng.integers(0, word.size - CLIP_SAMPLES + 1))
        out[:] = word[start:start + CLIP_SAMPLES]
        return out, -1, -1          # -1 => position unknown, flagged downstream
    lo = margin_samples
    hi = CLIP_SAMPLES - word.size - margin_samples
    off = int(rng.integers(lo, hi + 1)) if hi > lo else max(0, (CLIP_SAMPLES - word.size) // 2)
    out[off:off + word.size] = word
    return out, off, off + word.size


def cut_partial(word: np.ndarray, rng: np.random.Generator,
                cov_lo: float, cov_hi: float) -> tuple[np.ndarray, float]:
    """Produce a window holding only part of the keyword — the sliding-window
    failure mode. Absent these, a predecessor fired on 49.7% of realistic
    windows against 10.7% on its curated clip set."""
    cov = float(rng.uniform(cov_lo, cov_hi))
    keep = max(1, int(word.size * cov))
    out = np.zeros(CLIP_SAMPLES, dtype=np.float32)
    if rng.random() < 0.5:                      # word entering the window
        seg = word[word.size - keep:]
        off = int(rng.integers(0, max(1, CLIP_SAMPLES - seg.size)))
    else:                                       # word leaving the window
        seg = word[:keep]
        off = int(rng.integers(max(0, CLIP_SAMPLES - seg.size - 2000),
                               max(1, CLIP_SAMPLES - seg.size)))
    seg = seg[:CLIP_SAMPLES]
    out[off:off + seg.size] = seg
    return out, cov


def random_crop(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """One 1.0 s window from a longer recording, zero-padded if too short."""
    if x.size == CLIP_SAMPLES:
        return x.astype(np.float32)
    if x.size > CLIP_SAMPLES:
        s = int(rng.integers(0, x.size - CLIP_SAMPLES + 1))
        return x[s:s + CLIP_SAMPLES].astype(np.float32)
    out = np.zeros(CLIP_SAMPLES, dtype=np.float32)
    off = int(rng.integers(0, CLIP_SAMPLES - x.size + 1))
    out[off:off + x.size] = x
    return out


def peak_normalize(x: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    pk = float(np.abs(x).max())
    if pk < 1e-9:
        return x
    return (x * (10 ** (target_db / 20.0) / pk)).astype(np.float32)


def rms_dbfs(x: np.ndarray) -> float:
    return float(20 * np.log10(np.sqrt((x.astype(np.float64) ** 2).mean()) + 1e-12))


def measure_snr_db(x: np.ndarray) -> float:
    """Loudest decile vs quietest decile over 20 ms frames."""
    f = 320
    n = x.size // f
    if n < 10:
        return float("nan")
    e = np.sort((x[:n * f].astype(np.float64).reshape(n, f) ** 2).mean(axis=1))
    lo = e[: max(1, n // 10)].mean()
    hi = e[-max(1, n // 10):].mean()
    if lo <= 0 or hi <= 0:
        return float("nan")
    # Digital silence makes `lo` vanish and the ratio explode (an 809 dB value
    # appeared in the first smoke build). Clamp to a physically meaningful range.
    return float(np.clip(10 * np.log10(hi / lo), -10.0, 90.0))
