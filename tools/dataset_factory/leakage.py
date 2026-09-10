"""Leakage detection — the build FAILS if any of these fire.

Leakage is not a warning. A dataset that leaks produces a number that means
nothing, and the number will look good, which is worse than looking bad.

SUFFICIENCY is a separate question and returns WARNINGS, not failures. "This
test set is too small to conclude much" and "this test set is contaminated" are
different problems: the first makes a number imprecise, the second makes it a
lie. Bundling them meant a small-but-clean dataset could not be built at all,
which blocked measuring whether real audio helps at the very point that
question mattered. A dataset carrying warnings is marked PROVISIONAL and every
number from it must be reported as such.
"""

from __future__ import annotations

from collections import defaultdict


CHECKS = [
    "identical audio across splits (sha256)",
    "duplicate clips within a split (sha256)",
    "voice_id appearing in more than one split",
    "speaker_id appearing in more than one split",
    "source utterance (voice+text) spanning splits",
    "held-out recording session appearing outside the test split",
    "synthetic audio present in the test split",
    "augmented audio present in the test split",
    "test split empty or missing a required class",
]


def check(manifest: list[dict]) -> tuple[list[str], list[str], dict]:
    """Return (failures, warnings, stats). Empty failures == no leakage."""
    fails: list[str] = []
    warns: list[str] = []
    stats: dict = {}

    by_split = defaultdict(list)
    for m in manifest:
        by_split[m["split"]].append(m)

    # --- 1. identical audio across splits ---------------------------------
    hash_splits = defaultdict(set)
    for m in manifest:
        hash_splits[m["sha256"]].add(m["split"])
    cross = {h: s for h, s in hash_splits.items() if len(s) > 1}
    stats["hashes_crossing_splits"] = len(cross)
    if cross:
        ex = list(cross.items())[:3]
        fails.append(f"{len(cross)} identical audio hash(es) appear in multiple splits, "
                     f"e.g. {[(h[:12], sorted(s)) for h, s in ex]}")

    # --- 2. duplicates within a split -------------------------------------
    dups = 0
    for split, rows in by_split.items():
        seen = set()
        for m in rows:
            if m["sha256"] in seen:
                dups += 1
            seen.add(m["sha256"])
    stats["duplicate_clips"] = dups
    if dups > len(manifest) * 0.02:
        fails.append(f"{dups} duplicate clips ({100*dups/max(1,len(manifest)):.1f}% of the set)")

    # --- 3. voice_id across splits ----------------------------------------
    voice_splits = defaultdict(set)
    for m in manifest:
        if m["voice_id"]:
            voice_splits[m["voice_id"]].add(m["split"])
    bad_voices = {v: s for v, s in voice_splits.items() if len(s) > 1}
    # The single real human speaker is a DECLARED exception: with one speaker a
    # speaker-disjoint split is impossible, so they span splits by construction.
    #
    # D-015 changed what that exception costs. Real audio is now allowed in
    # TRAIN - keeping it out produced an honest evaluation that said the model
    # does not work, and no feature transform closes the domain gap
    # (DOMAIN_GAP_ANALYSIS.md 1). The control that replaces it is SESSION
    # disjointness, checked below: whichever recording session is quarantined
    # for test must appear in no other split. That is a real control, and unlike
    # the old rule it is achievable with one speaker.
    declared = {v for v in bad_voices if v.startswith("SPK_PILOT")}
    undeclared = {v: s for v, s in bad_voices.items() if v not in declared}
    stats["voices_crossing_splits"] = len(undeclared)
    stats["declared_real_speaker_exception"] = sorted(declared)
    if undeclared:
        fails.append(f"{len(undeclared)} voice_id(s) span multiple splits, "
                     f"e.g. {list(undeclared.items())[:3]}")

    # --- 3b. recording SESSION disjointness -------------------------------
    sess_splits = defaultdict(set)
    for m in manifest:
        sid = m.get("session_id") or ""
        if sid:
            sess_splits[sid].add(m["split"])
    test_sessions = {k for k, v in sess_splits.items() if "test" in v}
    leaked = {k: sorted(v) for k, v in sess_splits.items()
              if "test" in v and len(v) > 1}
    stats["real_sessions"] = {k: sorted(v) for k, v in sorted(sess_splits.items())}
    stats["heldout_test_sessions"] = sorted(test_sessions)
    stats["sessions_leaking_out_of_test"] = len(leaked)
    if leaked:
        fails.append(f"held-out session(s) appear outside test: {leaked} — the "
                     "session-disjoint control is broken, so no real-audio "
                     "number from this build means anything")
    if sess_splits and not test_sessions:
        fails.append("no recording session is quarantined for test — real "
                     "positives in test must come from a session absent from "
                     "train and validation")

    # --- 4. speaker_id across splits --------------------------------------
    spk_splits = defaultdict(set)
    for m in manifest:
        if m["speaker_id"]:
            spk_splits[m["speaker_id"]].add(m["split"])
    bad_spk = {k: v for k, v in spk_splits.items()
               if len(v) > 1 and not k.startswith("SPK_PILOT")}
    stats["speakers_crossing_splits"] = len(bad_spk)
    if bad_spk:
        fails.append(f"{len(bad_spk)} speaker_id(s) span multiple splits, "
                     f"e.g. {list(bad_spk.items())[:3]}")

    # --- 5. source utterance spanning splits ------------------------------
    utt_splits = defaultdict(set)
    for m in manifest:
        if m["voice_id"] and m["text"]:
            utt_splits[(m["voice_id"], m["text"])].add(m["split"])
    bad_utt = {k: v for k, v in utt_splits.items()
               if len(v) > 1 and not str(k[0]).startswith("SPK_PILOT")}
    stats["utterances_crossing_splits"] = len(bad_utt)
    if bad_utt:
        fails.append(f"{len(bad_utt)} source utterance(s) span splits — an augmented "
                     "derivative of a training clip is in another split")

    # --- 6/7. test split purity -------------------------------------------
    test = by_split.get("test", [])
    synth_in_test = [m for m in test if m["synthetic"] == "true"]
    stats["synthetic_in_test"] = len(synth_in_test)
    # Synthetic audio in test is permitted ONLY for negative classes; the
    # positive test set must be real human audio or the detection rate is
    # a statement about TTS, not about speech.
    synth_pos_test = [m for m in synth_in_test if m["class"] == "positive"]
    stats["synthetic_positives_in_test"] = len(synth_pos_test)
    if synth_pos_test:
        fails.append(f"{len(synth_pos_test)} SYNTHETIC positives in the test split — "
                     "detection rate would measure TTS, not speech")

    aug_test = [m for m in test
                if m["augmentation"] not in ("none", "mic_band", "")]
    stats["augmented_in_test"] = len(aug_test)
    if aug_test:
        fails.append(f"{len(aug_test)} augmented clips in the test split "
                     "(only mic_band channel matching is allowed)")

    # --- 8. test viability -------------------------------------------------
    stats["test_size"] = len(test)
    if not test:
        fails.append("test split is EMPTY")
    else:
        classes = {m["class"] for m in test}
        if "positive" not in classes:
            fails.append("test split contains NO positives")
        n_pos = sum(1 for m in test if m["class"] == "positive")
        stats["test_positives"] = n_pos
        # Sufficiency, not contamination. A 95% Wilson interval on a recall
        # measured over n positives is roughly +-35 pp at n=18 and +-10 pp at
        # n=200, so this governs how loudly a result may be stated, not whether
        # the dataset is sound.
        if n_pos < 20:
            warns.append(f"only {n_pos} test positives — a recall measured here "
                         f"carries roughly +-35 pp of uncertainty; treat every "
                         f"number as PROVISIONAL and directional only")
        elif n_pos < 100:
            warns.append(f"{n_pos} test positives — usable but imprecise "
                         f"(roughly +-15 pp on recall)")

    n_sessions = len(stats.get("heldout_test_sessions", []))
    if n_sessions == 1 and stats.get("test_positives", 0) < 20:
        warns.append("the held-out test set is ONE short session: it measures "
                     "one speaker on one day, and cannot separate session "
                     "effects from domain adaptation")

    stats["provisional"] = bool(warns)
    return fails, warns, stats
