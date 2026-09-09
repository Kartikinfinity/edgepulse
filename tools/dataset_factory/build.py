"""Dataset factory orchestrator.

Generates the complete demo dataset deterministically from config.py:

    TTS positives + real pilot positives
    partial-keyword negatives cut from positives
    TTS phonetic hard negatives (ksha / taks / shiil / neighbour / boundary)
    real human speech negatives (Speech Commands)
    background + silence
      -> augment (seeded) -> 1.0 s windows -> split -> manifest

Splits are assigned by VOICE, not by clip: every clip from a given TTS voice
lands in one split, so no voice leaks across. Real human audio is reserved for
validation/test because there is only one speaker.
"""

from __future__ import annotations

import csv
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import tts
from .audio import (apply_gain_db, apply_rir, change_speed, cut_partial,
                    measure_snr_db, mic_band_limit, mix_noise, peak_normalize,
                    extract_keyword, place_in_window, random_crop, read_wav,
                    rms_dbfs, rng_for,
                    seed_of, sha256_array, speech_span_ms, trim_silence,
                    write_wav, triangular)
from .config import (AUG, CLIP_SAMPLES, DATASET_VERSION, EDGE_MARGIN_MS,
                     MAX_KEYWORD_MS, MIN_KEYWORD_MS, MODEL_TARGET,
                     NEAR_HOMOPHONES, OUT_DIR, PARTIAL_COVERAGE, PILOT_DIR,
                     REAL_AUDIO_SPLITS, SPEECH_COMMANDS, SPLIT_FRACTIONS, SR,
                     TARGETS)

MARGIN = int(SR * EDGE_MARGIN_MS / 1000)

MANIFEST_FIELDS = [
    "clip_id", "filepath", "class", "sub_label", "model_target",
    "source_type", "speaker_id", "voice_id", "synthetic", "microphone",
    "source_corpus", "source_license", "text",
    "sample_rate", "duration_samples", "keyword_onset_ms", "keyword_offset_ms",
    "keyword_coverage", "speaking_rate", "length_scale",
    "augmentation", "snr_db", "gain_db", "rms_dbfs", "measured_snr_db",
    "split", "generation_seed", "sha256",
]


# ---------------------------------------------------------------------------
# noise / RIR pools
# ---------------------------------------------------------------------------
def load_noise_pool() -> dict[str, list[np.ndarray]]:
    """Real background audio, partitioned by split so training noise never
    appears in the validation/test mixes (leakage vector L-5)."""
    pool: list[tuple[str, np.ndarray]] = []
    bg = SPEECH_COMMANDS / "_background_noise_"
    if bg.is_dir():
        for f in sorted(bg.glob("*.wav")):
            try:
                x, sr = read_wav(f)
                pool.append((f"speech_commands/{f.stem}", np.asarray(x)))
            except Exception:
                pass
    # our own room tone, recorded on the actual INMP441
    for f in sorted(PILOT_DIR.rglob("*silence*.wav")):
        try:
            x, sr = read_wav(f)
            pool.append((f"inmp441/{f.stem}", np.asarray(x)))
        except Exception:
            pass
    out = defaultdict(list)
    for i, (name, x) in enumerate(pool):
        split = "train" if i % 5 < 3 else ("validation" if i % 5 == 3 else "test")
        out[split].append(x)
    if not out["validation"]:
        out["validation"] = out["train"][:1]
    if not out["test"]:
        out["test"] = out["train"][-1:]
    return dict(out), [n for n, _ in pool]


# ---------------------------------------------------------------------------
# split assignment
# ---------------------------------------------------------------------------
def split_for_voice(voice_id: str) -> str:
    """Deterministic, voice-level. All clips from one voice share a split."""
    r = rng_for("voicesplit", voice_id).random()
    if r < SPLIT_FRACTIONS["train"]:
        return "train"
    if r < SPLIT_FRACTIONS["train"] + SPLIT_FRACTIONS["validation"]:
        return "validation"
    return "test"


def voice_makes_positives(voice_id: str) -> bool:
    """Whether a TTS voice may contribute POSITIVES at all.

    The test split's positives must be real human audio, or the reported
    detection rate measures how well the model recognises a speech synthesiser.

    An earlier version *redirected* test-assigned voices to validation for
    positives only. That broke the "one voice, one split" invariant: the same
    voice's hard negatives still went to test, so 40 voices ended up spanning
    validation AND test. The leakage gate caught it on the full build.

    Excluding the voice from positives entirely is the correct fix - it keeps
    each voice in exactly one split, with no special cases.
    """
    return split_for_voice(voice_id) != "test"


# ---------------------------------------------------------------------------
# augmentation
# ---------------------------------------------------------------------------
def augment(x: np.ndarray, split: str, noise_pool: dict, rng: np.random.Generator,
            allow_speed: bool = False) -> tuple[np.ndarray, dict]:
    """Apply the seeded augmentation chain. The TEST split gets channel
    matching only — never synthetic noise, reverb, gain or speed."""
    meta = {"augmentation": [], "snr_db": "", "gain_db": ""}

    if AUG["band_limit_prob"] >= 1.0 or rng.random() < AUG["band_limit_prob"]:
        x = mic_band_limit(x)
        meta["augmentation"].append("mic_band")

    if split == "test":
        return x, meta

    if allow_speed and rng.random() < AUG["speed_prob"]:
        f = float(rng.uniform(*AUG["speed_range"]))
        x = change_speed(x, f)
        meta["augmentation"].append(f"speed{f:.3f}")

    if rng.random() < AUG["gain_prob"]:
        g = float(rng.uniform(*AUG["gain_db_range"]))
        x = apply_gain_db(x, g)
        meta["gain_db"] = f"{g:.1f}"
        meta["augmentation"].append("gain")

    if rng.random() < AUG["noise_prob"]:
        pool = noise_pool.get(split) or noise_pool.get("train") or []
        if pool:
            nz = pool[int(rng.integers(0, len(pool)))]
            snr = triangular(rng, AUG["snr_db_range"][0], AUG["snr_db_range"][1],
                             AUG["snr_db_mode"])
            x = mix_noise(x, nz, snr, rng)
            meta["snr_db"] = f"{snr:.1f}"
            meta["augmentation"].append("noise")

    pk = float(np.abs(x).max())
    if pk > 0.99:
        x = x * (0.99 / pk)
    # Gain augmentation on an already-quiet source can push a clip below the
    # usable floor (-73 dBFS seen in the first smoke build). Lift it back rather
    # than keep a clip the model can learn nothing from.
    r = rms_dbfs(x)
    if r < -55.0 and pk > 1e-6:
        x = apply_gain_db(x, min(24.0, -45.0 - r))
    return x.astype(np.float32), meta


# ---------------------------------------------------------------------------
# generators
# ---------------------------------------------------------------------------
def gen_tts_positives(rows: list, noise_pool: dict, limit: int | None,
                      log) -> tuple[int, int]:
    plan = tts.plan_positive_voices(TARGETS["positive_tts"])
    if limit:
        plan = plan[:limit]
    by_model = defaultdict(list)
    for p in plan:
        by_model[p["model"]].append(p)

    made = rejected = 0
    partials_made = 0
    want_partials = TARGETS["hard_negative_partial"]
    partial_every = max(1, len(plan) // max(1, want_partials))

    for mi, (model, items) in enumerate(sorted(by_model.items()), 1):
        log(f"  [{mi}/{len(by_model)}] {model}: {len(items)} utterances")
        for p in items:
            # Voices assigned to the test split contribute no positives at all
            # (see voice_makes_positives). Skip before spending synthesis time.
            if not voice_makes_positives(p["voice_id"]):
                continue
            try:
                word = tts.synthesize(model, p["text"], p["speaker_id"],
                                      p["length_scale"], p["noise_scale"], p["noise_w"])
            except Exception:
                rejected += 1
                continue
            if word.size < int(SR * 0.15):
                rejected += 1
                continue
            span = speech_span_ms(word, SR)
            # keyword must fit the window with margin, else it is not a positive
            if not (MIN_KEYWORD_MS <= span <= MAX_KEYWORD_MS):
                rejected += 1
                continue
            # The trimmed array (speech + padding) must also physically fit
            # inside 1.0 s with the edge margin, or place_in_window would crop
            # it and the ">=60 ms margin" guarantee would be silently violated.
            max_len = CLIP_SAMPLES - 2 * MARGIN
            if word.size > max_len:
                word = trim_silence(word, SR, pad_ms=5.0)
            if word.size > max_len:
                rejected += 1
                continue
            word = peak_normalize(word, -6.0)
            split = split_for_voice(p["voice_id"])
            rng = rng_for("posclip", p["voice_id"], p["idx"])
            clip, on, off = place_in_window(word, rng, MARGIN)
            clip, ameta = augment(clip, split, noise_pool, rng, allow_speed=True)
            rows.append(_row(
                cls="positive", sub="positive/tts", split=split,
                source_type="tts", speaker_id="", voice_id=p["voice_id"],
                synthetic="true", mic="synthetic",
                corpus=f"piper:{model}", lic="MIT (voice model); GPL-3.0 (engine)",
                text=p["text"], clip=clip,
                onset=on / SR * 1000, offset=off / SR * 1000, cov=1.0,
                rate=p["length_scale"], ameta=ameta,
                seed=seed_of("posclip", p["voice_id"], p["idx"]),
            ))
            made += 1

            # partial-keyword negatives, cut from this same utterance so they
            # inherit its split (leakage vector L-2)
            if partials_made < want_partials and (made % partial_every == 0):
                prng = rng_for("partial", p["voice_id"], p["idx"])
                pc, cov = cut_partial(word, prng, *PARTIAL_COVERAGE)
                pc, pmeta = augment(pc, split, noise_pool, prng)
                rows.append(_row(
                    cls="hard_negative", sub="hard_negative/partial", split=split,
                    source_type="tts_partial", speaker_id="", voice_id=p["voice_id"],
                    synthetic="true", mic="synthetic",
                    corpus=f"piper:{model}", lic="MIT (voice model); GPL-3.0 (engine)",
                    text=p["text"], clip=pc, onset="", offset="", cov=round(cov, 3),
                    rate=p["length_scale"], ameta=pmeta,
                    seed=seed_of("partial", p["voice_id"], p["idx"]),
                ))
                partials_made += 1
    return made, rejected, partials_made


def gen_hard_negatives(rows: list, noise_pool: dict, limit: int | None, log) -> int:
    n_phrases = sum(len(v) for v in NEAR_HOMOPHONES.values())
    per = max(1, TARGETS["near_homophone"] // max(1, n_phrases))
    plan = tts.plan_negative_phrases(NEAR_HOMOPHONES, per)
    if limit:
        plan = plan[:limit]
    by_model = defaultdict(list)
    for p in plan:
        by_model[p["model"]].append(p)

    made = 0
    for mi, (model, items) in enumerate(sorted(by_model.items()), 1):
        log(f"  [{mi}/{len(by_model)}] {model}: {len(items)} confusables")
        for j, p in enumerate(items):
            try:
                w = tts.synthesize(model, p["text"], p["speaker_id"],
                                   p["length_scale"], p["noise_scale"], p["noise_w"])
            except Exception:
                continue
            if w.size < int(SR * 0.10):
                continue
            w = peak_normalize(w, -6.0)
            split = split_for_voice(p["voice_id"])
            rng = rng_for("negclip", p["voice_id"], p["tier"], p["text"], p["idx"])
            clip, on, off = place_in_window(w, rng, MARGIN // 2)
            clip, ameta = augment(clip, split, noise_pool, rng)
            rows.append(_row(
                cls="near_homophone", sub=f"near_homophone/{p['tier']}", split=split,
                source_type="tts", speaker_id="", voice_id=p["voice_id"],
                synthetic="true", mic="synthetic",
                corpus=f"piper:{model}", lic="MIT (voice model); GPL-3.0 (engine)",
                text=p["text"], clip=clip, onset=on / SR * 1000,
                offset=off / SR * 1000, cov="", rate=p["length_scale"],
                ameta=ameta, seed=seed_of("negclip", p["voice_id"], p["text"], p["idx"]),
            ))
            made += 1
    return made


def gen_speech_negatives(rows: list, noise_pool: dict, limit: int | None, log) -> int:
    """Real human speech from Speech Commands (CC BY 4.0). Split by the corpus's
    own speaker hash so its speakers do not leak across our splits either."""
    if not SPEECH_COMMANDS.is_dir():
        log("  Speech Commands NOT FOUND — skipping (dataset will be weaker)")
        return 0
    words = [d for d in sorted(SPEECH_COMMANDS.iterdir())
             if d.is_dir() and not d.name.startswith("_")]
    want = limit or TARGETS["speech_negative"]
    per_word = max(1, want // max(1, len(words)))
    made = 0
    for w in words:
        files = sorted(w.glob("*.wav"))
        if not files:
            continue
        rng = rng_for("sc", w.name)
        pick = files if len(files) <= per_word else [
            files[i] for i in rng.choice(len(files), per_word, replace=False)]
        for f in pick:
            if made >= want:
                break
            try:
                x, sr = read_wav(f)
            except Exception:
                continue
            spk = f.stem.split("_")[0]
            split = split_for_voice(f"sc:{spk}")
            r = rng_for("scclip", f.stem)
            clip = random_crop(x, r)
            clip, ameta = augment(clip, split, noise_pool, r)
            rows.append(_row(
                cls="speech_negative", sub=f"speech_negative/{w.name}", split=split,
                source_type="public", speaker_id=f"sc:{spk}", voice_id=f"sc:{spk}",
                synthetic="false", mic="unknown",
                corpus="google_speech_commands_v0.02", lic="CC BY 4.0",
                text=w.name, clip=clip, onset="", offset="", cov="",
                rate="", ameta=ameta, seed=seed_of("scclip", f.stem),
            ))
            made += 1
    return made


def gen_background_silence(rows: list, noise_pool: dict, log) -> tuple[int, int]:
    """Background from Speech Commands _background_noise_ + our own INMP441
    room tone. Silence from real room tone, not synthesised zeros."""
    srcs: list[tuple[str, str, str, Path]] = []
    bg = SPEECH_COMMANDS / "_background_noise_"
    if bg.is_dir():
        for f in sorted(bg.glob("*.wav")):
            srcs.append(("background", "google_speech_commands_v0.02", "CC BY 4.0", f))
    for f in sorted(PILOT_DIR.rglob("*silence*.wav")):
        srcs.append(("silence", "own_inmp441", "project-owned", f))
    if not srcs:
        return 0, 0

    nb = ns = 0
    want_bg, want_si = TARGETS["background"], TARGETS["silence"]
    bg_srcs = [s for s in srcs if s[0] == "background"]
    si_srcs = [s for s in srcs if s[0] == "silence"]

    for cls, want, pool in (("background", want_bg, bg_srcs), ("silence", want_si, si_srcs)):
        if not pool:
            continue
        per = max(1, want // len(pool))
        for kind, corpus, lic, f in pool:
            try:
                x, sr = read_wav(f)
            except Exception:
                continue
            for k in range(per):
                r = rng_for(cls, f.stem, k)
                clip = random_crop(x, r)
                split = split_for_voice(f"bg:{f.stem}")
                clip, ameta = augment(clip, split, noise_pool, r)
                rows.append(_row(
                    cls=cls, sub=f"{cls}/{f.stem}", split=split,
                    source_type="public" if corpus != "own_inmp441" else "real_device",
                    speaker_id="", voice_id=f"bg:{f.stem}",
                    synthetic="false",
                    mic="inmp441" if corpus == "own_inmp441" else "unknown",
                    corpus=corpus, lic=lic, text="", clip=clip,
                    onset="", offset="", cov="", rate="", ameta=ameta,
                    seed=seed_of(cls, f.stem, k),
                ))
                if cls == "background":
                    nb += 1
                else:
                    ns += 1
    return nb, ns


def gen_real_positives(rows: list, noise_pool: dict, log) -> tuple[int, int]:
    """Real human INMP441 keyword recordings.

    ONE speaker, so these go to validation/test ONLY. They are what makes the
    evaluation real; putting them in train would leave nothing honest to test on
    and would still not buy speaker independence.
    """
    files = sorted(PILOT_DIR.rglob("*takshila*.wav"))
    if not files:
        log("  no real keyword recordings found")
        return 0, 0
    kept = rejected = 0
    for f in files:
        try:
            x, sr = read_wav(f)
        except Exception:
            rejected += 1
            continue
        # LOCATE the keyword inside the 3 s recording and cut it out. Trimming
        # alone is not enough: room tone keeps the array far longer than 1 s, and
        # place_in_window would then random-crop it, potentially producing a
        # "positive" containing no keyword at all.
        # Measure the span on the ORIGINAL recording, where real silence exists
        # to establish a noise floor. Measuring it on the already-extracted
        # segment re-thresholds against speech itself and collapses the span -
        # it dropped 15/17 usable takes to 5/17 before this was corrected.
        span = speech_span_ms(x, SR)
        if not (MIN_KEYWORD_MS <= span <= MAX_KEYWORD_MS):
            rejected += 1
            continue
        w = extract_keyword(x, SR)
        if w is None:
            rejected += 1
            continue
        if w.size > CLIP_SAMPLES - 2 * MARGIN:
            w = extract_keyword(x, SR, pad_ms=10.0)
            if w is None or w.size > CLIP_SAMPLES - 2 * MARGIN:
                rejected += 1
                continue
        # session-disjoint substitute for speaker-disjoint: alternate by file
        # so both validation and test contain real keyword audio.
        split = REAL_AUDIO_SPLITS[kept % len(REAL_AUDIO_SPLITS)]
        for k in range(6):        # offset sampling: the real inference distribution
            r = rng_for("realpos", f.stem, k)
            clip, on, off = place_in_window(peak_normalize(w, -6.0), r, MARGIN)
            clip, ameta = augment(clip, split, noise_pool, r)
            rows.append(_row(
                cls="positive", sub="positive/real_inmp441", split=split,
                source_type="real_device", speaker_id="SPK_PILOT_01",
                voice_id="SPK_PILOT_01", synthetic="false", mic="inmp441",
                corpus="own_inmp441", lic="project-owned", text="Takshila",
                clip=clip, onset=on / SR * 1000, offset=off / SR * 1000, cov=1.0,
                rate="", ameta=ameta, seed=seed_of("realpos", f.stem, k),
            ))
        # partial-keyword windows from real audio - the most realistic negatives
        for k in range(2):
            r = rng_for("realpart", f.stem, k)
            pc, cov = cut_partial(peak_normalize(w, -6.0), r, *PARTIAL_COVERAGE)
            pc, ameta = augment(pc, split, noise_pool, r)
            rows.append(_row(
                cls="hard_negative", sub="hard_negative/partial_real", split=split,
                source_type="real_device", speaker_id="SPK_PILOT_01",
                voice_id="SPK_PILOT_01", synthetic="false", mic="inmp441",
                corpus="own_inmp441", lic="project-owned", text="Takshila",
                clip=pc, onset="", offset="", cov=round(cov, 3), rate="",
                ameta=ameta, seed=seed_of("realpart", f.stem, k),
            ))
        kept += 1
    return kept, rejected


# ---------------------------------------------------------------------------
def _row(*, cls, sub, split, source_type, speaker_id, voice_id, synthetic, mic,
         corpus, lic, text, clip, onset, offset, cov, rate, ameta, seed) -> dict:
    return dict(
        _clip=clip, cls=cls, sub=sub, split=split, source_type=source_type,
        speaker_id=speaker_id, voice_id=voice_id, synthetic=synthetic, mic=mic,
        corpus=corpus, lic=lic, text=text, onset=onset, offset=offset, cov=cov,
        rate=rate, ameta=ameta, seed=seed,
    )


def write_all(rows: list, out_dir: Path, log) -> list[dict]:
    """Write audio + manifests. Returns finished manifest rows."""
    manifest: list[dict] = []
    counters: Counter = Counter()
    for i, r in enumerate(rows):
        cls, split = r["cls"], r["split"]
        counters[(split, cls)] += 1
        n = counters[(split, cls)]
        clip_id = f"{split}_{cls}_{n:06d}"
        rel = f"{split}/{cls}/{clip_id}.wav"
        path = out_dir / rel
        x = r["_clip"]
        if x.size != CLIP_SAMPLES:
            y = np.zeros(CLIP_SAMPLES, dtype=np.float32)
            y[:min(CLIP_SAMPLES, x.size)] = x[:CLIP_SAMPLES]
            x = y
        write_wav(path, x, SR)
        am = r["ameta"]
        manifest.append({
            "clip_id": clip_id, "filepath": rel, "class": cls,
            "sub_label": r["sub"], "model_target": MODEL_TARGET[cls],
            "source_type": r["source_type"], "speaker_id": r["speaker_id"],
            "voice_id": r["voice_id"], "synthetic": r["synthetic"],
            "microphone": r["mic"], "source_corpus": r["corpus"],
            "source_license": r["lic"], "text": r["text"],
            "sample_rate": SR, "duration_samples": CLIP_SAMPLES,
            "keyword_onset_ms": ("" if r["onset"] == "" else f"{float(r['onset']):.1f}"),
            "keyword_offset_ms": ("" if r["offset"] == "" else f"{float(r['offset']):.1f}"),
            "keyword_coverage": r["cov"], "speaking_rate": "",
            "length_scale": r["rate"],
            "augmentation": "+".join(am["augmentation"]) or "none",
            "snr_db": am["snr_db"], "gain_db": am["gain_db"],
            "rms_dbfs": f"{rms_dbfs(x):.1f}",
            "measured_snr_db": f"{measure_snr_db(x):.1f}",
            "split": split, "generation_seed": r["seed"],
            "sha256": sha256_array(x),
        })
        if (i + 1) % 2000 == 0:
            log(f"    written {i+1}/{len(rows)}")

    mdir = out_dir / "manifests"
    mdir.mkdir(parents=True, exist_ok=True)
    for split in ("train", "validation", "test"):
        sub = [m for m in manifest if m["split"] == split]
        with (mdir / f"{split}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
            w.writeheader()
            w.writerows(sub)
    with (mdir / "all.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(manifest)
    return manifest
