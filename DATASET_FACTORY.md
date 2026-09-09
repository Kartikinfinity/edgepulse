# DATASET_FACTORY.md — how to regenerate the dataset from a fresh clone

The audio is **not** in Git (~740 MB generated + 670 MB of voice models). What *is* committed is
everything needed to reproduce it byte-for-byte: the factory code, the configuration, the master
seed, and the manifests of what was produced.

---

## 1. Reproduce it

```bash
# 1. environment
bash scripts/setup.sh --dev            # or scripts\setup.ps1 -Dev on Windows
python -m pip install piper-tts

# 2. download the TTS voice models (~670 MB, ~90 s)
python tools/download_voices.py

# 3. build (~40 min: ~9,600 TTS renderings + ~23,000 clips)
python tools/build_dataset.py --force

# 4. the build self-checks; it exits non-zero if anything leaks
echo $?          # 0 = clean
```

**Determinism.** Every stochastic choice derives from `MASTER_SEED` in
`tools/dataset_factory/config.py` via a SHA-256 of a stable key
(`rng_for("posclip", voice_id, index)`). Same seed + same sources ⇒ same audio. Each clip also
records its own `generation_seed` in the manifest, so a single clip can be regenerated without
rebuilding the set.

**What is NOT reproducible without the original inputs:** the 14 real INMP441 recordings under
`data/recordings/`. Those are irreplaceable and are backed up separately — the factory consumes
them, it cannot recreate them.

## 2. What the factory does

```
                 real INMP441 recordings (14)      Piper voices (~1,090)
                            |                              |
                    locate + extract keyword        synthesize keyword
                            |                              |
                            +--------- 1.0 s window --------+
                            |          (offset sampled)     |
                            |                               +--> partial cuts (25-85%)
                            v                               v
   Speech Commands ---> augment (seeded) ---> split by VOICE ---> manifest
   (unknown speech,        mic band-limit        train/val/test        + QA report
    background)            noise / gain / speed                        + leakage gate
```

| Stage | Module |
|---|---|
| Configuration, seeds, targets | `tools/dataset_factory/config.py` |
| Audio primitives, seeded augmentation | `tools/dataset_factory/audio.py` |
| Piper synthesis + voice planning | `tools/dataset_factory/tts.py` |
| Orchestration, splits, manifests | `tools/dataset_factory/build.py` |
| Leakage assertions (build FAILS) | `tools/dataset_factory/leakage.py` |
| QA report | `tools/dataset_factory/report.py` |
| CLI | `tools/build_dataset.py` |

## 3. Where things land

| Path | Contents | In Git? |
|---|---|---|
| `data/tts_voices/` | Piper `.onnx` models, ~670 MB | ❌ downloadable |
| `data/dataset/{train,validation,test}/<class>/*.wav` | the clips | ❌ regenerable |
| `data/dataset/manifests/*.csv` | full per-clip metadata | ❌ (copied below) |
| `data/dataset/DATASET_REPORT.txt` | QA report | ❌ (copied below) |
| **`dataset_manifest/*.csv.gz`** | **gzipped manifests — the provenance record** | ✅ **tracked** |
| **`dataset_manifest/DATASET_REPORT.txt`** | **QA report** | ✅ **tracked** |
| **`dataset_manifest/build_config.json`** | **exact build parameters** | ✅ **tracked** |
| `data/recordings/` | raw human recordings | ❌ **irreplaceable, back up** |

## 4. Changing the dataset

Edit `tools/dataset_factory/config.py` and rebuild. The knobs that matter:

| Setting | Effect |
|---|---|
| `MASTER_SEED` | changes every stochastic choice; produces a different but equally valid dataset |
| `TARGETS[...]` | per-class clip counts — see `DATASET_SIZE_RATIONALE.md` before raising these |
| `VOICE_MODELS[...].weight` | how the positive budget is split across voice families |
| `NEAR_HOMOPHONES` | the confusable vocabulary (do not add random words — see below) |
| `AUG[...]` | augmentation probabilities and ranges |
| `SPLIT_FRACTIONS` | train/validation/test proportions |
| `MIN/MAX_KEYWORD_MS` | the admissible duration window; tied to the 1.0 s model input |

**Bump `DATASET_VERSION` whenever you change any of these**, or two different datasets will
claim the same identity.

## 5. Rules the factory enforces so you cannot break them by accident

These are code, not documentation:

1. **The test split's positives are real human audio only.** Synthetic positives are routed to
   validation instead. *(This fired on the first smoke build and caught 3 TTS positives that had
   landed in test — the detection rate would have been a statement about a speech synthesiser.)*
2. **The test split is never augmented** beyond the microphone channel match.
3. **A voice belongs to exactly one split.** All clips from a given TTS voice share it.
4. **Partial-keyword negatives inherit the split of the positive they were cut from**, so an
   augmented derivative can never cross.
5. **Training noise comes only from the training noise partition.**
6. **A keyword is located before it is windowed.** A long recording is never randomly cropped —
   that could produce a "positive" containing no keyword. *(Also caught by the smoke build.)*
7. **The build exits non-zero on any leakage.** It is a gate, not a report.

## 6. Honest limits, restated here so they travel with the code

- **One human speaker.** ~1,090 TTS voices are not 1,090 speakers. **No speaker-independence
  claim is possible** from this dataset.
- **The test set holds ~7 independent human utterances.** Six window offsets of one utterance are
  six views of one event. The 95 % CI on a clip-level detection rate is roughly **±35 pp** —
  enough to distinguish "works" from "does not", nothing finer.
- **The headline number must come from continuous audio** (false alarms per hour over a long
  negative stream), where the denominator is time rather than utterance count.
- **TTS is a training device.** It is not evidence about human speech, and the dataset is
  structured so that it cannot accidentally become evidence.
