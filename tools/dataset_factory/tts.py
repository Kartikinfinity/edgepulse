"""Piper TTS generation — positives and phonetic hard negatives.

Voice diversity is the whole point: multi-speaker models give ~1,090 distinct
voices, including L2-ARCTIC (non-native English, our target population) and
Indic voices that render the ksha conjunct natively. See
docs/DATASET_RESEARCH.md 5.

TTS is used for TRAINING breadth. It is never used in the test split, and it is
never presented as equivalent to real speakers.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .audio import resample_to, rng_for, trim_silence
from .config import (KEYWORD_TEXT, LENGTH_SCALES, NOISE_SCALES, NOISE_W_SCALES,
                     SR, VOICE_MODELS, VOICES_DIR)

_CACHE: dict[str, object] = {}

INDIC_LANG = {"hi_IN": "hi", "mr_IN": "mr", "te_IN": "te", "ml_IN": "ml"}


def available_models() -> list[str]:
    """Voice models actually present on disk."""
    return [n for n in VOICE_MODELS if (VOICES_DIR / f"{n}.onnx").is_file()]


def load_voice(name: str):
    if name in _CACHE:
        return _CACHE[name]
    from piper import PiperVoice
    p = VOICES_DIR / f"{name}.onnx"
    v = PiperVoice.load(str(p), config_path=str(p) + ".json")
    _CACHE[name] = v
    return v


def voice_speaker_count(name: str) -> int:
    cfg = json.loads((VOICES_DIR / f"{name}.onnx.json").read_text(encoding="utf-8"))
    return int(cfg.get("num_speakers", 1))


def model_sample_rate(name: str) -> int:
    cfg = json.loads((VOICES_DIR / f"{name}.onnx.json").read_text(encoding="utf-8"))
    return int(cfg["audio"]["sample_rate"])


def texts_for(name: str) -> list[str]:
    """Keyword spellings appropriate to this model's language."""
    tag = VOICE_MODELS[name]["tag"]
    if tag != "indic":
        return list(KEYWORD_TEXT[tag])
    lang = INDIC_LANG.get(name.split("-")[0], "hi")
    return list(KEYWORD_TEXT["indic"].get(lang, KEYWORD_TEXT["indic"]["hi"]))


def synthesize(name: str, text: str, speaker_id: int | None,
               length_scale: float, noise_scale: float,
               noise_w: float) -> np.ndarray:
    """Render one utterance at 16 kHz, silence-trimmed. Returns float32 [-1,1]."""
    from piper import SynthesisConfig
    voice = load_voice(name)
    sc = SynthesisConfig(speaker_id=speaker_id, length_scale=length_scale,
                         noise_scale=noise_scale, noise_w_scale=noise_w,
                         normalize_audio=True)
    parts = []
    for ch in voice.synthesize(text, syn_config=sc):
        if hasattr(ch, "audio_int16_array"):
            a = np.asarray(ch.audio_int16_array).ravel()
        else:
            a = np.frombuffer(ch.audio_int16_bytes, dtype="<i2")
        parts.append(a)
    if not parts:
        return np.zeros(0, dtype=np.float32)
    x = np.concatenate(parts).astype(np.float32) / 32768.0
    x = resample_to(x, model_sample_rate(name), SR)
    return trim_silence(x, SR)


def plan_positive_voices(n_target: int) -> list[dict]:
    """Choose (model, speaker_id) pairs weighted per config, then assign each a
    deterministic set of synthesis parameters. Returns one dict per utterance.

    Voices are the diversity axis, so we spread across as many distinct speakers
    as possible before repeating any of them.
    """
    models = available_models()
    if not models:
        return []
    total_w = sum(VOICE_MODELS[m]["weight"] for m in models)
    plan: list[dict] = []

    for m in models:
        share = VOICE_MODELS[m]["weight"] / total_w
        want = max(1, int(round(n_target * share)))
        nspk = min(voice_speaker_count(m), VOICE_MODELS[m]["n"])
        txts = texts_for(m)
        rng = rng_for("plan_pos", m)

        # distinct speakers first, cycling only when we run out
        spk_order = list(range(nspk)) if nspk > 1 else [None]
        rng.shuffle(spk_order)

        for i in range(want):
            spk = spk_order[i % len(spk_order)]
            r = rng_for("pos", m, spk, i)
            plan.append(dict(
                model=m,
                tag=VOICE_MODELS[m]["tag"],
                speaker_id=spk,
                voice_id=f"{m}#{spk if spk is not None else 0}",
                text=txts[int(r.integers(0, len(txts)))],
                length_scale=float(LENGTH_SCALES[int(r.integers(0, len(LENGTH_SCALES)))]),
                noise_scale=float(NOISE_SCALES[int(r.integers(0, len(NOISE_SCALES)))]),
                noise_w=float(NOISE_W_SCALES[int(r.integers(0, len(NOISE_W_SCALES)))]),
                idx=i,
            ))
    return plan


def plan_negative_phrases(phrases: dict[str, list[str]], per_phrase: int) -> list[dict]:
    """Spread each confusable phrase across many voices.

    English-language models only: these are English/romanised confusables, and
    an Indic model would mangle them. The ksha family is deliberately included
    here in romanised form so English voices produce the /kSH/ snippet that
    FakeWake identifies as the decisive factor.
    """
    models = [m for m in available_models() if VOICE_MODELS[m]["tag"] != "indic"]
    if not models:
        return []
    plan: list[dict] = []
    for tier, words in phrases.items():
        for w_i, phrase in enumerate(words):
            rng = rng_for("neg", tier, phrase)
            for k in range(per_phrase):
                m = models[int(rng.integers(0, len(models)))]
                nspk = min(voice_speaker_count(m), VOICE_MODELS[m]["n"])
                spk = int(rng.integers(0, nspk)) if nspk > 1 else None
                plan.append(dict(
                    model=m,
                    tag=VOICE_MODELS[m]["tag"],
                    speaker_id=spk,
                    voice_id=f"{m}#{spk if spk is not None else 0}",
                    text=phrase,
                    tier=tier,
                    length_scale=float(LENGTH_SCALES[int(rng.integers(0, len(LENGTH_SCALES)))]),
                    noise_scale=float(NOISE_SCALES[int(rng.integers(0, len(NOISE_SCALES)))]),
                    noise_w=float(NOISE_W_SCALES[int(rng.integers(0, len(NOISE_W_SCALES)))]),
                    idx=k,
                ))
    return plan
