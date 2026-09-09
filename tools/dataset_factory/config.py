"""Dataset factory configuration — every knob in one place, all seeded.

The dataset is reproducible from this file plus the manifests: a fresh clone
that runs `python tools/build_dataset.py` with the same MASTER_SEED and the same
sources regenerates byte-identical audio.

Sizes are justified in DATASET_SIZE_RATIONALE.md, not chosen by feel.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config.paths import DATASET_ROOT, PROJECT_ROOT, RECORDINGS_ROOT  # noqa: E402

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
MASTER_SEED = 20260910
DATASET_VERSION = "takshila-demo-1.0"
KEYWORD = "Takshila"

# ---------------------------------------------------------------------------
# Audio format — fixed by ARCHITECTURE.md 3 / KWS_ENGINE_DECISION.md 4
# ---------------------------------------------------------------------------
SR = 16000
CLIP_SAMPLES = 16000          # exactly 1.000 s
DTYPE = "<i2"                 # signed PCM16 LE

# Positive-class rule (DEMO_DATASET_SPEC.md 4 / RESEARCH_DATASET_ROADMAP.md 4):
# the complete keyword must sit inside the window with this much margin at each
# edge, so the detector never sees a truncated onset labelled "complete".
EDGE_MARGIN_MS = 60
MAX_KEYWORD_MS = 880          # 1000 - 2*60; measured human range was 220-720 ms
MIN_KEYWORD_MS = 250

# Partial-keyword negatives: windows holding this fraction of the keyword.
PARTIAL_COVERAGE = (0.25, 0.85)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
VOICES_DIR = PROJECT_ROOT / "data" / "tts_voices"
CACHE_DIR = PROJECT_ROOT / "data" / "factory_cache"
OUT_DIR = DATASET_ROOT                     # data/dataset
PILOT_DIR = RECORDINGS_ROOT / "PILOT"

# External corpora. Absent sources are skipped with a warning, never faked.
SPEECH_COMMANDS = Path(r"D:\speech_commands\data")

# ---------------------------------------------------------------------------
# Classes
#   6-way label for analysis; 3-way model_target for training.
# ---------------------------------------------------------------------------
CLASSES = ("positive", "near_homophone", "hard_negative",
           "speech_negative", "background", "silence")

MODEL_TARGET = {
    "positive": "keyword",
    "near_homophone": "unknown",
    "hard_negative": "unknown",
    "speech_negative": "unknown",
    "background": "background",
    "silence": "background",
}

# ---------------------------------------------------------------------------
# TTS voices.
#   Multi-speaker models give many distinct voices from one file. Speaker
#   indices are the diversity axis; length_scale/noise give within-voice
#   variation. Indic voices render the ksha conjunct natively, which en_US
#   voices cannot - see docs/DATASET_RESEARCH.md 5.
# ---------------------------------------------------------------------------
VOICE_MODELS = {
    # name                        n_speakers  role
    "en_US-libritts_r-medium":   dict(n=904, tag="en_us_multi",  weight=0.34),
    "en_GB-vctk-medium":         dict(n=109, tag="en_gb_multi",  weight=0.16),
    "en_US-l2arctic-medium":     dict(n=24,  tag="en_nonnative", weight=0.22),  # Indian-accented English
    "en_US-arctic-medium":       dict(n=18,  tag="en_us_multi",  weight=0.08),
    "mr_IN-google-medium":       dict(n=9,   tag="indic",        weight=0.06),
    "hi_IN-pratham-medium":      dict(n=1,   tag="indic",        weight=0.04),
    "hi_IN-priyamvada-medium":   dict(n=1,   tag="indic",        weight=0.04),
    "hi_IN-rohan-medium":        dict(n=1,   tag="indic",        weight=0.03),
    "te_IN-maya-medium":         dict(n=1,   tag="indic",        weight=0.02),
    "ml_IN-arjun-medium":        dict(n=1,   tag="indic",        weight=0.01),
}

# Keyword spellings per model family. Indic models get native script so the
# ksha conjunct is realised properly; English models get romanisations that
# cover the anglicised variants (V7 "Taxila", V4 hyper-articulated).
KEYWORD_TEXT = {
    "en_us_multi":  ["Takshila", "Tuk-sheela", "Taksheela", "Tak shee laa"],
    "en_gb_multi":  ["Takshila", "Tuk-sheela", "Taksheela"],
    "en_nonnative": ["Takshila", "Taksheela", "Tuk-sheela"],
    "indic": {
        "hi": ["तक्षिला", "तक्षशिला"],
        "mr": ["तक्षिला"],
        "te": ["తక్షిల"],
        "ml": ["തക്ഷില"],
    },
}

# Synthesis variation. length_scale > 1 is slower. Capped so the rendered
# keyword stays inside MAX_KEYWORD_MS after silence trimming.
LENGTH_SCALES = (0.85, 0.95, 1.05, 1.15)
NOISE_SCALES = (0.55, 0.667, 0.80)      # prosodic variability
NOISE_W_SCALES = (0.6, 0.8, 1.0)        # phoneme-duration variability

# ---------------------------------------------------------------------------
# Hard negatives — derived in KEYWORD_SELECTION.md 13, not random words.
# FakeWake: false accepts concentrate on shared phonetic snippets, and
# Levenshtein distance does NOT predict them. Random English words exercise the
# wrong part of the boundary.
# ---------------------------------------------------------------------------
NEAR_HOMOPHONES = {
    # Tier 1 - the ksha family. Frequent in real Indian speech, shares the
    # decisive /kSH/ middle. HIGHEST priority, must be in train.
    "ksha": ["shiksha", "raksha", "lakshya", "moksha", "daksha", "paksha",
             "rakshak", "suraksha", "pariksha", "aksha", "vriksha", "diksha",
             "kaksha", "bhiksha", "samiksha", "apeksha", "upeksha", "akshay",
             "lakshmi", "takshak"],
    # Tier 2 - /taeks/ onset family.
    "taks": ["taxi", "tax", "taxes", "taxable", "tax law", "tax filing",
             "taxonomy", "tactical", "taxidermy", "tax free", "taximeter",
             "taxpayer", "tax return", "taxing", "tactics", "tax slab",
             "taxied", "taxonomic"],
    # Tier 3 - stressed /SHiil/ nucleus.
    "shiil": ["Sheila", "she'll", "shield", "shielding", "shilling", "Shilpa",
              "she looks", "Shimla", "she left", "shear law", "Sheila's"],
    # Tier 4 - full-word neighbours. NOTE: "Takshashila" is a NEGATIVE (V9) -
    # it is a different word and admitting it would widen the boundary.
    "neighbour": ["Takshak", "Takshashila", "Taxila", "Takshaka", "Thakshila",
                  "Dakshila", "Lakshila", "Takshira", "Takshina", "Takshan",
                  "Takshit", "Taksheel"],
    # Tier 5 - cross-word reconstructions the sliding window may see.
    "boundary": ["talk she'll ah", "attack shield", "that's a shield",
                 "take a seat Sheila", "tax she left", "stock she'll allow",
                 "look Sheila", "black shield", "the tax he laid",
                 "shock she'll adapt", "tak sheela", "back shift law"],
}

# ---------------------------------------------------------------------------
# Augmentation. Distributions chosen for realistic deployment, not exhaustively
# crossed - applying everything to everything manufactures a distribution that
# does not occur. Ranges informed by the measured pilot (post-HPF SNR 3.7-33 dB).
# ---------------------------------------------------------------------------
AUG = dict(
    noise_prob=0.75,
    snr_db_range=(3.0, 30.0),
    snr_db_mode=18.0,           # triangular, weighted toward realistic room SNR
    gain_prob=0.6,
    gain_db_range=(-12.0, 6.0),
    rir_prob=0.35,
    speed_prob=0.30,
    speed_range=(0.92, 1.08),   # +-8%: measured durations stay inside the window
    band_limit_prob=1.0,        # ALWAYS on synthetic/public - domain adaptation
)

# INMP441 channel model (datasheet: -3 dB at 60 Hz and 15 kHz; the pipeline's
# mel floor starts at 125 Hz so sub-125 content is irrelevant downstream).
MIC_HPF_HZ = 70.0
MIC_LPF_HZ = 7600.0

# ---------------------------------------------------------------------------
# Target counts — justified in DATASET_SIZE_RATIONALE.md
# ---------------------------------------------------------------------------
TARGETS = dict(
    positive_tts=5400,          # ~900 distinct voices x ~6 renderings
    positive_real=None,         # however many pilot takes pass QC
    near_homophone=4200,        # 74 phrases x many voices
    hard_negative_partial=2200, # cut from positives - the critical class
    speech_negative=8000,       # Speech Commands, real human speech
    background=2400,
    silence=700,
)

# ---------------------------------------------------------------------------
# Splits.
#   With ONE human speaker a speaker-disjoint split is impossible for real
#   audio. The substitute control is SESSION-disjoint, and no speaker-
#   independence claim may be made (docs/DATASET_RESEARCH.md 9).
#   TTS voices ARE split disjointly by speaker index - a voice used in train
#   never appears in val or test.
# ---------------------------------------------------------------------------
SPLIT_FRACTIONS = dict(train=0.80, validation=0.12, test=0.08)
REAL_AUDIO_SPLITS = ("validation", "test")   # real human audio is for evaluation
