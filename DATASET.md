# DATASET.md

```
DATASET STATUS:
    NOT YET CREATED

KEYWORD:
    RECOMMENDED "Takshila" - research complete, awaiting confirmation
    (KEYWORD_SELECTION.md, DECISIONS.md D-011 proposed)

NEXT OBJECTIVE:
    Confirm the keyword, then write the recording protocol and run one
    pilot session before recruiting speakers.
```

**Last updated:** 2026-09-09 · **Status:** reset · See `DATASET_RESET_AUDIT.md` for the audit
that produced this state and `DECISIONS.md` **D-010** for the decision.

---

## 1. Current state

There is **no approved dataset for this project**. Keyword selection was reopened by the reset
and the research is now **complete**: `KEYWORD_SELECTION.md` recommends **`Takshila`**, awaiting
your confirmation before it becomes binding (D-011).

| Item | State |
|---|---|
| Approved dataset | ❌ none |
| Selected keyword | 🟡 **`Takshila` recommended**, awaiting confirmation |
| Raw recordings | ❌ none collected |
| Feature caches | ❌ none |
| Trained model | ❌ none, in this project or any predecessor still in scope |
| Dataset statistics | ❌ none that may be quoted |

**Nothing in this repository may be trained, validated, tested, benchmarked or documented
against the deprecated corpus.** Any figure you find attributed to it is out of scope.

## 2. What was deprecated, and why it matters

A previously supplied corpus (`solvani_kws_release`, 21,267 one-second WAVs) was removed from
the project by instruction. It is gone from the active tree; its 674 MB on disk has been
quarantined, not deleted, and is the user's to dispose of.

Its statistics, splits, class counts, augmentation scheme and keyword are **all out of scope**
and must not inform any decision here.

### The one thing worth carrying forward is a lesson, not a number

That corpus failed for a structural reason, and the failure is instructive when *designing*
a new dataset:

> Its positive class was ~110 unique utterances from **one speaker** in two rooms, inflated
> ×7.2 by augmentation to look like 790 clips. The negative class drew on thousands of
> speakers. Augmentation copies information; it does not add any.

A predecessor project demonstrated **on hardware** that this asymmetry cannot be repaired
downstream: neither decision-logic tuning nor adding more public negative speech fixed it.

**Design consequences for the new dataset — these are requirements, not suggestions:**

1. **Speaker diversity in the positive class is the primary design variable.** Plan for many
   speakers from the start. A single-speaker positive class caps the entire project.
2. **Keep every raw, uncut recording.** The previous corpus could not be re-cut at different
   offsets or extended in context because its raw sessions were lost. Store raw sessions
   alongside the curated clips.
3. **Design positional spread deliberately.** A corpus of centred, complete words trains a
   model that fails on sliding windows, where most windows contain a word *fragment*.
4. **Splits must be recording-disjoint and, unlike last time, speaker-disjoint.** Only a
   speaker-disjoint test split can support a speaker-independence claim.
5. **Plan the hard-negative set as a first-class component**, not an afterthought — and put
   the hardest confusables in *training*, not only in validation/test.
6. **Record the evaluation protocol before collecting**, so the corpus is built to support
   streaming evaluation rather than clip accuracy (`DECISIONS.md` D-005).

## 3. Where the new dataset will live

| What | Path | Note |
|---|---|---|
| Raw source recordings | `<repo>/data/recordings` (`SIH_RECORDINGS_ROOT`) | **keep permanently** |
| Built / curated dataset | `<repo>/data/dataset` (`SIH_DATASET_ROOT`) | git-ignored |
| Features, checkpoints, models | `<repo>/artifacts` | git-ignored |

Both resolve through `config/paths.py` and are overridable in `.env`. Neither exists yet.
Audio never enters Git; a fingerprint mechanism will be reintroduced once there is a dataset
whose structure is known.

## 4. Tooling that survived the reset

Two dataset-agnostic measurement tools, rewritten to take a directory argument and to assume
nothing about layout, keyword or class names:

```bash
python tools/audio_probe.py <dir>          # format uniformity, duration, RMS/peak, clipping
python tools/audio_probe_bands.py <dir>    # speech-band energy fraction; where the word sits
```

Use them on new recordings **while collecting**, not after training. Catching a format or
level problem during a session is cheap; discovering it after training is not.

Removed with the reset, recoverable from git history at commit `2c4500c` if ever needed:
`DATASET_SETUP.md`, `scripts/verify_dataset.py`, `scripts/generate_dataset_manifest.py`,
`tools/analyze_manifests.py`, `dataset_manifest/`.

## 5. What the next phase must do

In order. **None of it has started, and none of it may be skipped.**

1. ~~**Keyword selection.**~~ **DONE** — `KEYWORD_SELECTION.md` delivers 18 candidates, a
   weighted 20-criterion matrix, phonetic analysis, hard-negative derivation, an ISRO/SIH
   contextual analysis, an ESP32/WakeNet suitability analysis and a licence audit.
   **Recommendation: `Takshila`**, pending confirmation (D-011 proposed).
   Full data specification is in `KEYWORD_SELECTION.md` §§13–15.
2. **Dataset design specification**, written *before* any recording: target speaker count,
   utterances per speaker, environments, distances, positional-offset strategy, hard-negative
   word list, background sources, split policy (speaker-disjoint), and the licence position
   for any external corpus.
3. **Recording protocol** — prompts, sample rate and format, session structure, and the
   quality bar for accepting or rejecting a take.
4. **Collection**, keeping raw sessions.
5. **Curation and build**, producing a documented, versioned dataset with a fresh manifest.
6. **Only then** feature extraction, the streaming evaluation harness, and training.

The evaluation methodology in `DECISIONS.md` D-005 survives the reset unchanged and governs
step 6: headline numbers come from a streaming simulation over continuous audio, never from
centred clips.
