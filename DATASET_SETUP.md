# DATASET_SETUP.md

How to put the dataset on a new machine and **prove** it is the right one.

The 21,267 WAV files (0.64 GB) are deliberately **not** in Git. What *is*
committed is a fingerprint — `dataset_manifest/` — precise enough to detect a
single flipped byte.

---

## 1. What you need

| Field | Value |
|---|---|
| Dataset name | `solvani_kws_release` |
| Version | **`solvani_kws_release-1.0`** |
| Keyword | `solvani` |
| Original archive | `training Dataset (don't open)-20260908T164308Z-1-001.zip` → nested `solvani_kws_release.zip` (570.5 MB) |
| Expanded size | 685,589,976 bytes across 21,285 files (21,267 WAV + 18 CSV/Markdown) |
| Root SHA-256 | `34a1a266e094c329df6551c2525ae13430a74823497b0dda12273b7ad243de90` |

The dataset is **not publicly downloadable** — it is supplied with the project.
Copy it from the original machine, the original archive, or your own backup.

## 2. Where to put it

**Default (recommended):**

```
<repository root>/data/solvani_kws_release/
```

Nothing else needs configuring; `config/paths.py` finds it.

**Somewhere else** (another drive, a shared corpus directory) — set it in `.env`:

```
SIH_DATASET_ROOT=/mnt/data/solvani_kws_release      # Linux, absolute
SIH_DATASET_ROOT=D:\corpora\solvani_kws_release     # Windows, absolute
SIH_DATASET_ROOT=../shared/solvani_kws_release      # relative to the repo root
```

Confirm what resolved:

```bash
python config/paths.py
```

## 3. Extracting from the original archive

The archive nests a second zip. On the original machine this two-step
extraction filled a full disk once — extract to a volume with **≥ 2 GB free**.

```bash
# Linux / macOS
unzip "training Dataset (don't open)-*.zip" -d /tmp/sih-outer
unzip "/tmp/sih-outer/training Dataset (don_t open)/solvani_kws_release.zip" -d data/
# -> data/solvani_kws_release/
```

```powershell
# Windows PowerShell
Expand-Archive ".\training Dataset (don't open)-*.zip" -DestinationPath "$env:TEMP\sih-outer"
Expand-Archive "$env:TEMP\sih-outer\training Dataset (don_t open)\solvani_kws_release.zip" -DestinationPath ".\data"
```

If the extracted path ends up as `data/solvani_kws_release/solvani_kws_release`,
move the inner directory up one level. `verify_dataset.py` will tell you.

> ⚠ **Do not** move the WAVs through anything lossy — a cloud-sync folder that
> rewrites files, or a zip round-trip with a re-encode step. Checksums will
> fail and you will not know which clips changed.

## 4. Expected layout

```
data/solvani_kws_release/
├── README.md
├── dataset_balanced/                    4,084 clips - fast iteration loop
│   ├── README.md
│   ├── REPORT.md
│   ├── manifests/
│   │   ├── train.csv
│   │   ├── validation.csv
│   │   └── test.csv
│   ├── train/{positive,negative,background}/*.wav
│   ├── validation/{positive,negative,background}/*.wav
│   └── test/{positive,negative,background}/*.wav
└── dataset_full/                       17,183 clips - full negative diversity
    └── (identical structure)
```

Manifest CSV columns: `filepath, label, original_source, speaker, environment,
augmentation, snr_db, duration, split, license, source_dataset, source_id`.
Paths inside a CSV are relative to that variant's root.

## 5. Expected counts

Every clip: **mono · 16 kHz · 16-bit PCM · exactly 16,000 frames (1.000 s)**.

### `dataset_full` — 17,183 clips

| split | positive | negative | background | total | manifest rows |
|---|---:|---:|---:|---:|---:|
| train | 693 | 6,849 | 7,497 | 15,039 | 15,039 |
| validation | 80 | 815 | 890 | 1,785 | 1,785 |
| **test** | **17** | 163 | 179 | 359 | 359 |

### `dataset_balanced` — 4,084 clips

| split | positive | negative | background | total | manifest rows |
|---|---:|---:|---:|---:|---:|
| train | 693 | 1,386 | 1,176 | 3,255 | 3,255 |
| validation | 80 | 297 | 252 | 629 | 629 |
| **test** | **17** | 99 | 84 | 200 | 200 |

Positive clips are **identical** in both variants.

### Manifest CSV checksums (SHA-256, first 16 hex)

| variant | train | validation | test |
|---|---|---|---|
| `dataset_full` | `7c252439155861d9` | `75a07eba2eebb262` | `a0de6eeebd4173ba` |
| `dataset_balanced` | `cbb7de6d3346b7b3` | `f5a239ff83b609ff` | `797c594546b64649` |

Full digests are in `dataset_manifest/manifest.json`.

## 6. Verify

```bash
python scripts/verify_dataset.py            # layout + counts + CSV hashes + 200 sampled files
python scripts/verify_dataset.py --full     # every one of 21,285 files (~90 s)
python scripts/verify_dataset.py --sample 2000
```

`--full` also recomputes the single **root SHA-256** and compares it against the
manifest. That is the strongest available statement that two machines hold
byte-identical data.

**Run `--full` once when the dataset first lands on a machine, and again before
publishing any result.** The spot-check is for day-to-day use.

Exit codes: `0` pass · `1` mismatch · `2` dataset or manifest missing.

## 7. How the fingerprint works

| File | Size | Contents |
|---|---:|---|
| `dataset_manifest/manifest.json` | ~3 KB | version, expected root, layout, per-split/class counts, manifest-CSV digests, totals, root hash |
| `dataset_manifest/CHECKSUMS.sha256` | ~2.6 MB | one `<sha256>  <relative/posix/path>` line per file, sorted |

`root_sha256` is the SHA-256 of the checksums file's exact bytes — a single
value that changes if any file's **content, name or presence** changes. It
equals `checksums_file_sha256` by construction; that is intended.

Relative POSIX paths are used throughout so a Windows checkout and a Linux
checkout produce the same digests.

## 8. If the dataset legitimately changes

Only when the data itself is genuinely replaced — not to silence a failure:

```bash
python scripts/generate_dataset_manifest.py
git add dataset_manifest/
git commit -m "data: regenerate dataset fingerprint for <reason>"
```

Bump `DATASET_VERSION` in `scripts/generate_dataset_manifest.py` at the same
time, and say why in `BUILD_LOG.md`. A silently regenerated manifest destroys
the guarantee it exists to provide.

## 9. Known limitations — read before training

These are measured, documented in `DATASET.md`, and must not be rediscovered:

1. **~110 unique positive utterances from ONE speaker (`speaker_01`), two rooms.** The 790 positive clips are ×7.2 augmentation of those 110. This is the project's binding constraint.
2. **17 unique positive utterances in the test split** — roughly ±20 percentage points on any rate computed from it.
3. **Speaker-independence cannot be measured** from this data. Never claim it.
4. Phonetic hard negatives: only **10 unique TTS phrases**, and the three hardest (`so many`, `sol vani`, `solvany`) appear only in validation/test, never in train.
5. Splits **are** genuinely recording-disjoint — 0 of 2,387 source recordings span a split. The leakage check passes.
6. Clips are 1.0 s windows containing the **whole** word; the device sees fragments. Training and evaluation must both account for this (`DATASET.md` §7, `DECISIONS.md` D-005).
7. The **raw uncut recordings are not available**. Positives cannot be re-cut at different offsets; new positive audio must be recorded or synthesised.

## 10. Optional external corpora

`D:\speech_commands` (Google Speech Commands v0.02, 5.37 GB) existed on the
original machine and is the corpus the dataset's `speech_commands` negatives
came from. **No phase requires it.** If you have a copy:

```
SIH_SPEECH_COMMANDS_ROOT=/path/to/speech_commands
```

It is exposed as `config.paths.SPEECH_COMMANDS_ROOT` and is `None` when unset.
