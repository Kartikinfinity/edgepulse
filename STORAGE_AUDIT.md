# STORAGE_AUDIT.md

**Date:** 2026-09-09 · **Author:** Claude (inspection only in Phase 1; nothing deleted)
**Scope:** recover safe space on C:, decide whether the SIH project can live on C: as one
self-contained tree, and locate the raw `Desktop\data` recording tree.

All figures are measured with `Get-ChildItem -Recurse -Force | Measure-Object Length -Sum`
or `Get-CimInstance Win32_LogicalDisk`. Nothing here is estimated unless labelled *projected*.

---

## 1. Current C: state

| Metric | Value |
|---|---|
| Volume | `C:` "OS SSD", NTFS |
| Physical device | 128 GB **NVMe SSD** (`128GB SSD`) |
| Capacity | 118.35 GB (127,079,018,496 B) |
| Used | 117.85 GB |
| **Free** | **0.50 GB (541,429,760 B) — 0.43 %** |
| pagefile.sys | **on D:, not C:** (system-managed) |
| hiberfil.sys | absent (hibernation already off) |
| swapfile.sys | 0.25 GB on C: |
| Shadow-copy storage | **unknown** — `vssadmin` requires elevation, not run |

The 0.50 GB currently free is space this session recovered on 2026-09-09 by deleting its own
failed extraction artifact (see §9).

### C: top-level

| GB | Path |
|---:|---|
| 73.53 | `C:\Users` |
| 28.13 | `C:\Windows` |
| 9.90 | `C:\Program Files` |
| 9.02 | `C:\Program Files (x86)` |
| 3.56 | `C:\ProgramData` |
| 0.20 | `C:\$Recycle.Bin` |
| 0.15 | `C:\Python314` |
| 0.05 | `C:\SWSetup` |

### `C:\Users\Menon` (73.53 GB)

`AppData` **57.41** · OneDrive 3.75 · `.platformio` 2.96 · `My project` 1.71 · `.vscode` 0.95 ·
`.antigravity-ide` 0.80 · `.antigravity` 0.78 · `.docker` 0.66 · `.codex` 0.60 · `.rustup` 0.55 ·
`.local` 0.53 · `.gemini` 0.51 · `miniforge3` 0.51 · `.android` 0.50 · rest < 0.4 each.

### `AppData\Local` (the 52 GB block)

| GB | Item | Classification |
|---:|---|---|
| 9.91 | `Programs` | installed applications — **PROTECTED** |
| 8.88 | `Arduino15` | 6.78 installed cores (**PROTECTED**) + **2.03 `staging` download cache (SAFE)** |
| **6.84** | `npm-cache` | **pure cache — SAFE** |
| 4.68 | `Packages` | Store-app data — **PROTECTED / personal** |
| 3.97 | `Android` | Android SDK — **PROTECTED** |
| **3.66** | `pip` | **pure cache — SAFE** |
| 3.39 | `Google` | Chrome profile — **PROTECTED / personal** |
| 2.29 | `Docker` | Docker Desktop data — **PROTECTED (uncertain contents)** |
| 1.57 | `WisprFlow` | app data — PROTECTED |
| 1.42 | `Microsoft` | Edge/Office — PROTECTED / personal |
| 0.78 | `OpenAI` | app data — PROTECTED |
| 0.56 | `Perplexity` | app data — PROTECTED |
| 0.39 | `Temp` | mostly stale installer temp — **partly SAFE** |
| 0.36 | `BraveSoftware` | browser profile — **PROTECTED / personal** |
| 0.34 | `uv` | `cache/` + receipt — **cache SAFE** |
| ~1.5 | `*-updater` dirs | downloaded installers — plausible but ownership per-app, **NOT touched** |

`AppData\Roaming` (~5.4 GB): `npm` 1.46 (installed global packages, **not** a cache),
`Python` 1.01, `Notion` 0.61, `Claude` 0.57, `Code` 0.56, `Antigravity` 0.37, `UnityHub` 0.33,
`Cursor` 0.31, `uv` 0.19 (`tools/` = installed tools, **PROTECTED**).

---

## 2. Current D: and E: state

| | D: "DATA D" | E: "DATA E" |
|---|---|---|
| Device | WDC WD10EZEX 931.5 GB **SATA HDD** | same physical HDD |
| Capacity | 366.21 GB | 467.64 GB |
| Free | **337.62 GB (92.19 %)** | **445.79 GB (95.33 %)** |
| Notable | hosts **`pagefile.sys`**; user's personal files at root; prior-build ML dirs | project tree + third-party backup dirs |

**D: items relevant to this project (all PROTECTED, none deleted):**

| Size | Path | What it is |
|---:|---|---|
| 5.373 GB | `D:\speech_commands` | Google Speech Commands v0.02 corpus + tarball — real training data |
| 1.726 GB | `D:\sih-ml-env` | **working venv, Python 3.11 + TensorFlow 2.21.0, numpy 2.4.6, scipy 1.17.1** (prior build) |
| 0.417 GB | `D:\sih-ml-cache` | that venv's pip cache |
| 0.000 GB | `D:\sih-ml-tmp` | 18 small text files |

D: root also holds many personal documents (resumes, reports, installers, and
`github-recovery-codes.txt`). **D: root is off-limits.**

**E: items:** `E:\sih2026` (the project), plus `CFRBACKUP-*` / `cfrbackup-*` directories
belonging to third-party backup software — one was written **today** and is actively in use.
Not touched.

---

## 3. Largest space consumers on C: — ranked

1. `AppData\Local\Programs` 9.91 GB — installed apps
2. `Arduino15` 8.88 GB — 6.78 installed cores + 2.03 staging cache
3. `npm-cache` 6.84 GB — cache
4. `Packages` 4.68 GB — Store apps
5. `Android` 3.97 GB — SDK
6. `pip` 3.66 GB — cache
7. `Google` 3.39 GB — Chrome profile
8. `.platformio` 2.96 GB — 2.29 toolchains + 0.67 cache
9. `Windows\Installer` 2.83 GB — MSI repair store
10. `Docker` 2.29 GB

---

## 4. Cleanup candidates — every one with a reason

### 4a. Approved for Phase 2 (unambiguously regenerable, no personal data)

| # | Target | Size | Why it is safe |
|---|---|---:|---|
| C1 | `AppData\Local\npm-cache` | **6.84 GB** | npm's content-addressed download cache. `npm cache clean --force` is npm's own documented command; npm re-downloads any package it needs. Contains no source or config. |
| C2 | `AppData\Local\pip\cache` | **3.66 GB** | pip's HTTP/wheel cache. `pip cache purge` is pip's own command; wheels are re-fetched from PyPI on demand. |
| C3 | `Arduino15\staging\packages` | **2.03 GB** | 36 already-extracted installer archives (`xtensa-esp-elf-*.zip`, `esp32-*-libs-*.zip`, …). The extracted results live in `Arduino15\packages`, which is **kept**. Arduino IDE re-downloads only if a core is reinstalled. Verified by listing: every entry is a `.zip`/`.tar.bz2`/`.tar.gz` archive. |
| C4 | `.platformio\.cache` | **0.67 GB** | PlatformIO's package download cache (18 files). The installed toolchains in `.platformio\packages` are **kept**. PlatformIO regenerates this directory. |
| C5 | `AppData\Local\uv\cache` | **0.34 GB** | uv's package cache; `uv cache clean` is uv's own command. `Roaming\uv\tools` (installed tools) is **kept**. |
| C6 | Selected stale items in `AppData\Local\Temp` | **~0.30 GB** | `vscode-stable-user-x64-*` (196 MB, 4 days) and `cursor-ext-vsix` (101 MB, 3 days) are finished-installer staging dirs. Only items older than 2 days, and only ones not locked. |
| | **Total projected** | **≈ 13.8 GB** | |

### 4b. Identified, deliberately NOT deleted

| Item | Size | Why not |
|---|---:|---|
| Duplicate source archives on C: (`training Dataset…zip` 544.2 MB, `datasheetr…zip` 16.7 MB, `the whole story.pdf`, `sih_2026_kartik_v.1.pdf`) | **561.8 MB** | **Verified byte-identical (SHA-256) to copies already on `D:\`.** They are still the user's own files in the user's own folder. Flagged for the user's decision, not removed. |
| `Desktop\SIH 2026\.pio` | 0.098 GB | Prior build's PlatformIO build cache — regenerable, but it sits inside a project directory. Left alone. |
| `Windows\Installer` | 2.83 GB | Required for MSI repair/uninstall. Deleting it breaks application servicing. |
| WinSxS / DISM component cleanup | — | Would modify Windows servicing state. Excluded by the safety constitution. |
| `$Recycle.Bin` | 0.197 GB | Constitution: do not empty automatically. |
| `Docker` 2.29 GB, `Packages` 4.68 GB, `Google`/`BraveSoftware`/`Microsoft` profiles, `Programs`, `Android`, `Arduino15\packages`, `Roaming\npm`, `miniforge3`, `.rustup`, `.vscode`, `*-updater` dirs | ~35 GB | Installed software, personal browser/app data, or uncertain ownership. |
| `D:\speech_commands`, `D:\sih-ml-env`, `D:\sih-ml-cache` | 7.5 GB | Real training data and a working TF environment. On D:, which has 337 GB free — no reason to touch. |
| `E:\CFRBACKUP-*` | — | Third-party backup software, actively writing today. |

---

## 5. Explicitly protected (never touched in any phase)

Windows and `Windows\System32`, WinSxS, `Program Files`, `Program Files (x86)`, WindowsApps,
boot/recovery/EFI partitions, drivers, registry, **pagefile configuration (pagefile is on D:)**,
hibernation configuration, System Restore / shadow copies, user documents, Desktop/Downloads/
Pictures/Videos/Music, unrelated personal projects, browser profiles, application data,
credentials, SSH keys, API keys, `.env` files, `github-recovery-codes.txt` on D:, the SIH
dataset, the current project, and anything of uncertain purpose.

No recursive wildcard deletion is used anywhere. Each cleanup target is an explicit path.

---

## 6. Estimated recoverable space

**≈ 13.8 GB**, taking C: from 0.50 GB free to **≈ 14.3 GB free (12.1 % of capacity)**.

---

## 7. Space the project actually needs — measured plus projected

| Component | Size | Basis |
|---|---:|---|
| Extracted dataset (21,285 WAVs) | **0.639 GB** | measured, `E:\sih2026\data` |
| Source, docs, git history | **0.001 GB** | measured, 13 tracked files |
| Feature caches (waveform + MFCC, several augmented variants) | ~3.0 GB | projected: 17,183 × 16,000 × 2 B raw = 0.55 GB per waveform cache; 17,183 × 49 × 13 × 4 B = 0.044 GB per feature set; several variants across experiments |
| Model checkpoints across experiments | ~0.3 GB | projected from prior build's `model*/` dirs |
| PlatformIO build dir | ~0.2 GB | prior build measured **0.098 GB** |
| Project-local Python venv (TF + audio libs + faster-whisper) | ~4.0 GB | prior TF-only venv measured **1.726 GB**; audio + ASR stack roughly doubles it |
| faster-whisper model cache | ~0.5 GB | `base.en` int8 ≈ 0.15 GB, `small.en` ≈ 0.5 GB |
| Demo recordings, telemetry logs, evidence | ~0.5 GB | projected |
| Training/temp working headroom | ~1.0 GB | projected |
| **Project total** | **≈ 10 GB**, call it **12 GB with margin** | |

**Windows also needs headroom on its own system drive** — feature updates alone stage several
GB, plus temp and servicing. A conservative floor on a 118 GB volume is **~15 GB free**.

**Therefore C: would need ≈ 27 GB free to host this project safely.**

---

## 8. Risks

| # | Risk | Severity | Note |
|---|---|---|---|
| R1 | C: is at 0.43 % free | **High** | Risks Windows update failures, OneDrive sync errors, application crashes on write. Cleanup addresses this partially. |
| R2 | Even after full safe cleanup, C: reaches only ~14.3 GB free | **High** | Below the ~27 GB the project plus Windows headroom requires. Drives the Phase-5 decision. |
| R3 | E: is a **SATA HDD**, not SSD | Medium | Slower I/O over 21k small WAVs. Mitigated by caching features to a single `.npz` rather than re-reading per epoch. 16 GB RAM will cache the 0.64 GB dataset. |
| R4 | Third-party backup software writes to E: | Low | `CFRBACKUP-*` dirs active today; unrelated to `E:\sih2026`. |
| R5 | Shadow-copy storage on C: unknown | Unknown | `vssadmin` needs elevation. If System Restore holds several GB, more space exists — but changing it is excluded by the constitution. |
| R6 | 561.8 MB of duplicated source archives on C: | Low | Verified identical to D: copies; awaiting user decision. |

---

## 9. Recommended cleanup sequence

1. `npm cache clean --force` (or delete `npm-cache`) — largest single safe win, 6.84 GB.
2. `pip cache purge` — 3.66 GB.
3. Delete `Arduino15\staging\packages` contents — 2.03 GB. Keep `Arduino15\packages`.
4. Delete `.platformio\.cache` — 0.67 GB. Keep `.platformio\packages`.
5. `uv cache clean` — 0.34 GB.
6. Remove only the two named stale Temp staging dirs, skipping anything locked — ~0.30 GB.
7. Re-measure C:.
8. Apply the Phase-5 rule with the measured result.

Already performed before this audit, and recorded for completeness: deletion of
`C:\c\Users\...\solvani_kws_release.zip` (560,988,160 B), an artefact **this session created**
when a POSIX path was passed to `C:\Python314\python` and resolved to `C:\e\...`. It was a
duplicate of a file that still exists on D: and in the project. **Recovered 509 MB. No user
file was involved.**

---

## 10. Phase 2 results — executed cleanup

**C: free before: 519,274,496 B (0.48 GB) → after: 13,791,440,896 B (12.84 GB, 10.85 % of capacity)**
**Recovered: 13,272,166,400 B = 12.36 GB**

| # | Category | Method | Recovered |
|---|---|---|---:|
| C2 | pip download/wheel cache | `python -m pip cache purge` (pip's own command) — reported "Files removed: 3503 (3925.6 MB), Directories removed: 1948" | **3.93 GB** |
| C3 | `Arduino15\staging\packages` | `find … -maxdepth 1 -type f -delete` on that exact directory — 36 archives, 0 remaining, directory itself kept | **2.03 GB** |
| C4 | `.platformio\.cache` | `rm -rf` on that exact path | **0.68 GB** |
| C5 | `AppData\Local\uv\cache` | `rm -rf` on that exact path | **0.37 GB** |
| C1 | `npm-cache\_cacache` + `_logs` | `rm -rf` on those two exact paths. Identity confirmed first: `npm config get cache` returned exactly `C:\Users\Menon\AppData\Local\npm-cache`. **`_npx` kept.** | **~5.3 GB** |
| C6 | Two named stale Temp staging dirs (`vscode-stable-user-x64-l4po57i6de`, `cursor-ext-vsix`) | age-checked (both 3 days) then `rm -rf` | **~0.30 GB** |

No wildcard or recursive deletion was applied above an explicitly named directory.

### Post-cleanup integrity check — all present

`Arduino15\packages` (7.0 GB installed cores) · `Arduino15\staging` (dir kept) ·
`.platformio\packages` (2.4 GB toolchains) · `.platformio\platforms` · `Roaming\npm` (global
packages) · `Roaming\uv\tools` (197 MB) · `npm-cache\_npx` · `AppData\Local\pip` ·
`D:\sih-ml-env` · `D:\speech_commands` · `E:\sih2026` · both Desktop project folders.

### Tooling re-verified after the purges

git 2.51.2 · Python 3.14.0 / 3.13.9 · **pip 26.0.1 works** · **npm 11.6.1 works** · node v24.11.0 ·
**PlatformIO Core 6.1.19 works**, `espressif32` platform and all 9 packages intact ·
TensorFlow 2.20.0 + torch 2.8.0+cpu (Python 3.13) · TensorFlow 2.21.0 (`D:\sih-ml-env`) ·
project analysis scripts reproduce their documented output.

### Not touched, as promised

Recycle Bin, `Windows\Installer`, WinSxS/DISM, Docker, Store `Packages`, all browser profiles,
all personal documents on C:/D:, `Programs`, `Android`, `Arduino15\packages`, `Roaming\npm`,
`miniforge3`, `.rustup`, updater directories, D: root, `E:\CFRBACKUP-*`, pagefile, hibernation,
System Restore, registry.

---

## 11. Phase 3 — raw `Desktop\data` recording tree

**Result: it does not exist on this machine.** Confirmed by four independent searches across
**all three fixed drives (C:, D:, E:)**:

| Search | Result |
|---|---|
| Directories named `data`, depth ≤ 4 | only `C:\Python314\Lib\test\*\data`, three `node_modules\*\data`, `D:\speech_commands\data`, `E:\sih2026\data` |
| Directories whose name contains `solvani` (unlimited depth) | **only** `E:\sih2026\data\solvani_kws_release` |
| Directories matching `different distances\|room with fan\|classroom noise` — the manifest's own raw session folder names | **none** |
| Files matching `noise_00*.wav` — the manifest's raw file naming | **none** |

`C:\Users\Menon\OneDrive\Desktop\data` does not exist, and there is no non-OneDrive
`C:\Users\Menon\Desktop`.

**What does exist and is related** (all left untouched):

| Path | Size | Assessment |
|---|---:|---|
| `D:\speech_commands` | 5.373 GB, 105,842 files | Google Speech Commands v0.02 + tarball. This is the *external corpus* the dataset build drew its `speech_commands` negatives from — **not** the raw `solvani` recordings. **Safe and useful as an additional project data source** for negatives/background. |
| `D:\sih-ml-env` | 1.726 GB | Working venv: Python 3.11, **TensorFlow 2.21.0**, numpy 2.4.6, scipy 1.17.1. No librosa/soundfile/sklearn. Belongs to the prior "Sentinel" build. Usable, but adopting it would split the project across drives. |
| `D:\sih-ml-cache` | 0.417 GB | that venv's pip cache |
| `D:\sih-ml-tmp` | ~0 | 18 small text files |

**Consequence, unchanged from `DATASET.md` §9:** the 110 unique positive utterances cannot be
re-cut at different offsets or extended beyond 1.0 s of context. Any additional positive audio
must be newly recorded or synthesised. If the user still holds that tree on another machine or
in cloud storage, several Phase-D options improve materially.

---

## 12. Phase 5 — storage decision

### The arithmetic

| Quantity | Value |
|---|---:|
| C: free after cleanup | **12.84 GB** |
| Project total (measured + projected, §7) | **≈ 12 GB** |
| Windows headroom required on a 118 GB system volume | **≈ 15 GB** |
| **Required for C: to host the project** | **≈ 27 GB** |
| **Shortfall** | **≈ 14 GB** |

Placing the project on C: would leave roughly **0.8 GB free** — recreating precisely the
0-bytes-free condition this task was created to fix. Even a stripped project (dataset 0.64 +
features 3 + venv 4 = 7.6 GB) would leave ~5 GB, still below healthy headroom for a system
drive that must service Windows updates.

### Decision: **keep the entire project on `E:\sih2026`** (Phase 7 branch)

- **C: is not sufficient.** No migration is performed.
- The project stays as **one self-contained root on one drive**. Nothing is split.
- `E:` has **445.79 GB free (95.33 %)** — ~35× the project's projected lifetime footprint.

### What would have to change for C: to become viable

Roughly 14 GB more would be needed. The only remaining large targets are all excluded by the
safety constitution or are genuine installed software: `Windows\Installer` (2.83 GB, breaks MSI
servicing), WinSxS/DISM component cleanup (modifies Windows servicing), Store `Packages`
(4.68 GB, personal app data), `Docker` (2.29 GB, uncertain), `Android` SDK (3.97 GB),
`Arduino15\packages` (6.78 GB installed cores), `Programs` (9.91 GB installed apps), browser
profiles (~3.8 GB, personal). **Reaching 27 GB would require uninstalling software or deleting
personal data. Neither is acceptable, so the decision is stable.**

Optional, user's call only: the four source archives on the Desktop (**561.8 MB**, SHA-256
verified byte-identical to copies already on `D:\`) could be removed from C: for a further
0.55 GB. Still nowhere near the shortfall, and they are the user's files.

### Note on what "one drive" means here

`C:\Users\Menon\.platformio` (2.4 GB of compiler toolchains) stays on C:. That is a **tool
installation**, in the same category as `git.exe`, `python.exe` and the Arduino cores — not
project data. The project's own build output is directed to `E:\sih2026\.pio` via `build_dir`.
No project file, dataset file, artifact or environment lives outside `E:\sih2026`.

### Recorded risk

C: at 10.85 % free is workable but not comfortable for a system drive. It will refill over time
as caches regenerate — `pip`, `npm`, `uv`, PlatformIO and Arduino staging will all rebuild
naturally with use. Re-running the §9 sequence is safe and repeatable whenever C: gets tight.
