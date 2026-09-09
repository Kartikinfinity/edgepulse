"""Streaming MFCC front end — the single definition of the feature pipeline.

THIS FILE IS THE CONTRACT WITH THE FIRMWARE. Every constant here must be
mirrored bit-for-bit in C++ on the ESP32-S3, and `tools/verify_parity.py`
compares the two against golden vectors produced by this module.

Pipeline (ARCHITECTURE.md 3, verified in KWS_ENGINE_DECISION.md 4):

    int16 PCM @ 16 kHz mono
      -> frame 400 samples (25 ms), hop 320 samples (20 ms)
      -> periodic Hann window
      -> 512-point real FFT -> power spectrum
      -> 40 mel filters, 125-7500 Hz (Slaney-style triangular, area-normalised)
      -> natural log
      -> orthonormal DCT-II, keep 13 coefficients
      -> per-coefficient (mean, std) normalisation   <- TRAIN statistics only
      -> 49 x 13 float32, or int8 after quantisation

Two properties matter more than elegance here:
  1. Determinism - same input bytes, same output floats, every run.
  2. Streaming equivalence - computing frames one at a time as audio arrives
     must give exactly the result of computing them in a batch. The device has
     no choice but to stream; if the host does something subtly different, every
     accuracy number is meaningless. `frames_streaming()` exists to prove it.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Constants — mirrored in firmware/include/kws_features.h
# ---------------------------------------------------------------------------
SAMPLE_RATE = 16000
FRAME_LEN = 400            # 25 ms
FRAME_HOP = 320            # 20 ms  => 50 frames/s
FFT_SIZE = 512
N_MEL = 40
MEL_LOW_HZ = 125.0         # rejects the sub-100 Hz INMP441 drift
MEL_HIGH_HZ = 7500.0
N_MFCC = 13
N_FRAMES = 49              # 49 * 20 ms + 25 ms = 985 ms ~ 1.0 s context
CLIP_SAMPLES = 16000
LOG_FLOOR = 1e-10          # keeps log() finite on digital silence

FEATURE_SHAPE = (N_FRAMES, N_MFCC)


# ---------------------------------------------------------------------------
# Fixed tables — computed once, identical on host and device
# ---------------------------------------------------------------------------
def hann_periodic(n: int = FRAME_LEN) -> np.ndarray:
    """Periodic (not symmetric) Hann. numpy's np.hanning is SYMMETRIC and would
    differ from the device by one sample of phase — a small, silent mismatch."""
    return (0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / n)).astype(np.float64)


def hz_to_mel(f: np.ndarray | float) -> np.ndarray | float:
    return 2595.0 * np.log10(1.0 + np.asarray(f, dtype=np.float64) / 700.0)


def mel_to_hz(m: np.ndarray | float) -> np.ndarray | float:
    return 700.0 * (10.0 ** (np.asarray(m, dtype=np.float64) / 2595.0) - 1.0)


def mel_filterbank(n_mel: int = N_MEL, n_fft: int = FFT_SIZE,
                   sr: int = SAMPLE_RATE, lo: float = MEL_LOW_HZ,
                   hi: float = MEL_HIGH_HZ) -> np.ndarray:
    """Triangular mel filters over the power spectrum. Shape (n_mel, n_fft//2+1).

    Filters are NOT area-normalised: each triangle peaks at 1.0. That choice is
    arbitrary but must match the device, so it is stated rather than implied.
    """
    n_bins = n_fft // 2 + 1
    edges_mel = np.linspace(hz_to_mel(lo), hz_to_mel(hi), n_mel + 2)
    edges_hz = mel_to_hz(edges_mel)
    bin_freqs = np.linspace(0.0, sr / 2.0, n_bins)
    fb = np.zeros((n_mel, n_bins), dtype=np.float64)
    for m in range(n_mel):
        l, c, r = edges_hz[m], edges_hz[m + 1], edges_hz[m + 2]
        if r <= l:
            continue
        rising = (bin_freqs - l) / max(c - l, 1e-9)
        falling = (r - bin_freqs) / max(r - c, 1e-9)
        fb[m] = np.clip(np.minimum(rising, falling), 0.0, None)
    return fb


def dct2_matrix(n_out: int = N_MFCC, n_in: int = N_MEL) -> np.ndarray:
    """Orthonormal DCT-II. Shape (n_out, n_in).

    Orthonormal, not the unnormalised variant: a single global mean/std over a
    non-orthonormal DCT collapsed coefficients c2..c12 and training degenerated
    to the majority class in a previous build.
    """
    k = np.arange(n_out)[:, None]
    n = np.arange(n_in)[None, :]
    m = np.cos(np.pi * k * (2.0 * n + 1.0) / (2.0 * n_in))
    m *= np.sqrt(2.0 / n_in)
    m[0] *= np.sqrt(0.5)
    return m


HANN = hann_periodic()
MELFB = mel_filterbank()
DCT = dct2_matrix()


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
def pcm16_to_float(x: np.ndarray) -> np.ndarray:
    """int16 -> float64 in [-1, 1). Divisor is 32768, matching the firmware."""
    return np.asarray(x, dtype=np.float64) / 32768.0


def frame_to_mfcc(frame: np.ndarray) -> np.ndarray:
    """One 400-sample frame -> 13 MFCC. The exact operation the device performs."""
    if frame.shape[0] != FRAME_LEN:
        raise ValueError(f"frame must be {FRAME_LEN} samples, got {frame.shape[0]}")
    windowed = frame * HANN
    padded = np.zeros(FFT_SIZE, dtype=np.float64)
    padded[:FRAME_LEN] = windowed
    spec = np.fft.rfft(padded, n=FFT_SIZE)
    power = (spec.real ** 2 + spec.imag ** 2)
    mel = MELFB @ power
    log_mel = np.log(np.maximum(mel, LOG_FLOOR))
    return DCT @ log_mel


def frames_batch(pcm: np.ndarray) -> np.ndarray:
    """All frames at once. Returns (n_frames, N_MFCC) float64."""
    x = pcm16_to_float(pcm) if np.issubdtype(np.asarray(pcm).dtype,
                                             np.integer) else np.asarray(pcm, np.float64)
    n = 1 + max(0, (x.size - FRAME_LEN) // FRAME_HOP)
    out = np.zeros((n, N_MFCC), dtype=np.float64)
    for i in range(n):
        s = i * FRAME_HOP
        out[i] = frame_to_mfcc(x[s:s + FRAME_LEN])
    return out


class StreamingFrontEnd:
    """Frame-at-a-time front end — the device's actual mode of operation.

    Audio arrives in arbitrary chunks; whenever FRAME_LEN samples are available
    a frame is emitted and the buffer advances by FRAME_HOP. It holds a ring of
    the last N_FRAMES so a 49x13 tensor is always available without recomputing
    the window (`ARCHITECTURE.md` 2, component 4).
    """

    def __init__(self, n_frames: int = N_FRAMES):
        self.n_frames = n_frames
        self._buf = np.zeros(0, dtype=np.float64)
        self._ring = np.zeros((n_frames, N_MFCC), dtype=np.float64)
        self._filled = 0

    def reset(self) -> None:
        self._buf = np.zeros(0, dtype=np.float64)
        self._ring[:] = 0.0
        self._filled = 0

    def push(self, pcm_chunk: np.ndarray) -> list[np.ndarray]:
        """Feed a chunk; return the MFCC frames it completed."""
        a = np.asarray(pcm_chunk)
        x = pcm16_to_float(a) if np.issubdtype(a.dtype, np.integer) else a.astype(np.float64)
        self._buf = np.concatenate([self._buf, x])
        made = []
        while self._buf.size >= FRAME_LEN:
            f = frame_to_mfcc(self._buf[:FRAME_LEN])
            self._ring[:-1] = self._ring[1:]
            self._ring[-1] = f
            self._filled = min(self._filled + 1, self.n_frames)
            made.append(f)
            self._buf = self._buf[FRAME_HOP:]
        return made

    @property
    def ready(self) -> bool:
        return self._filled >= self.n_frames

    def window(self) -> np.ndarray:
        """The current N_FRAMES x N_MFCC context, oldest frame first."""
        return self._ring.copy()


def frames_streaming(pcm: np.ndarray, chunk: int = 320) -> np.ndarray:
    """Same as frames_batch, but computed incrementally. Used to PROVE the
    streaming path and the batch path agree — if they ever diverge, every
    accuracy number measured on the host is invalid for the device."""
    fe = StreamingFrontEnd()
    out = []
    a = np.asarray(pcm)
    for i in range(0, a.size, chunk):
        out.extend(fe.push(a[i:i + chunk]))
    return np.asarray(out, dtype=np.float64) if out else np.zeros((0, N_MFCC))


# ---------------------------------------------------------------------------
# Clip-level features + normalisation
# ---------------------------------------------------------------------------
def clip_features(pcm: np.ndarray) -> np.ndarray:
    """A 1.0 s clip -> exactly (N_FRAMES, N_MFCC) float32, unnormalised.

    A 16,000-sample clip yields 1 + (16000-400)//320 = 49 frames exactly, so no
    padding or truncation happens in practice; both are handled anyway so a
    slightly short clip cannot crash a training run.
    """
    a = np.asarray(pcm)
    if a.size < CLIP_SAMPLES:
        pad = np.zeros(CLIP_SAMPLES, dtype=a.dtype)
        pad[:a.size] = a
        a = pad
    elif a.size > CLIP_SAMPLES:
        a = a[:CLIP_SAMPLES]
    f = frames_batch(a)
    if f.shape[0] < N_FRAMES:
        f = np.vstack([f, np.zeros((N_FRAMES - f.shape[0], N_MFCC))])
    return f[:N_FRAMES].astype(np.float32)


def fit_normalisation(feats: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-coefficient mean/std over (N, 49, 13). TRAIN SPLIT ONLY."""
    flat = feats.reshape(-1, N_MFCC)
    mean = flat.mean(axis=0).astype(np.float32)
    std = flat.std(axis=0).astype(np.float32)
    std = np.maximum(std, 1e-6)
    return mean, std


def apply_normalisation(feats: np.ndarray, mean: np.ndarray,
                        std: np.ndarray) -> np.ndarray:
    return ((feats - mean) / std).astype(np.float32)


def describe() -> dict:
    """The configuration, for embedding in artifacts and the parity report."""
    return dict(
        sample_rate=SAMPLE_RATE, frame_len=FRAME_LEN, frame_hop=FRAME_HOP,
        fft_size=FFT_SIZE, window="hann_periodic", n_mel=N_MEL,
        mel_low_hz=MEL_LOW_HZ, mel_high_hz=MEL_HIGH_HZ, n_mfcc=N_MFCC,
        n_frames=N_FRAMES, clip_samples=CLIP_SAMPLES,
        dct="orthonormal_dct2", log_floor=LOG_FLOOR,
        normalisation="per_coefficient_mean_std_train_only",
        feature_shape=list(FEATURE_SHAPE),
    )
