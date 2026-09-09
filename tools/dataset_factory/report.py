"""Dataset QA report — everything needed to judge the dataset before training."""

from __future__ import annotations

from collections import Counter, defaultdict


def build_report(manifest: list[dict], stats: dict, fails: list[str],
                 elapsed_s: float) -> str:
    L: list[str] = []
    A = L.append
    n = len(manifest)
    A("=" * 78)
    A("DATASET QA REPORT — Takshila demo dataset")
    A("=" * 78)
    A(f"clips              {n:,}")
    A(f"total duration     {n * 1.0 / 3600:.2f} h  (every clip exactly 1.000 s)")
    A(f"build time         {elapsed_s/60:.1f} min")
    A("")

    A("--- CLASS BALANCE ---")
    cls = Counter(m["class"] for m in manifest)
    for c, k in cls.most_common():
        A(f"  {c:<18} {k:>7,}  {100*k/n:5.1f}%")
    A("")
    A("--- MODEL TARGET (3-way training label) ---")
    mt = Counter(m["model_target"] for m in manifest)
    for c, k in mt.most_common():
        A(f"  {c:<18} {k:>7,}  {100*k/n:5.1f}%")
    kw = mt.get("keyword", 0)
    A(f"  positive : negative ratio = 1 : {(n-kw)/max(1,kw):.1f}")
    A("")

    A("--- SPLITS ---")
    for s in ("train", "validation", "test"):
        rows = [m for m in manifest if m["split"] == s]
        if not rows:
            A(f"  {s:<12} EMPTY")
            continue
        cc = Counter(m["class"] for m in rows)
        A(f"  {s:<12} {len(rows):>7,}  {100*len(rows)/n:5.1f}%   "
          + " ".join(f"{k}={v}" for k, v in cc.most_common()))
    A("")

    A("--- REAL vs SYNTHETIC ---")
    syn = Counter(m["synthetic"] for m in manifest)
    A(f"  synthetic          {syn.get('true',0):>7,}  {100*syn.get('true',0)/n:5.1f}%")
    A(f"  real               {syn.get('false',0):>7,}  {100*syn.get('false',0)/n:5.1f}%")
    st = Counter(m["source_type"] for m in manifest)
    for k, v in st.most_common():
        A(f"    {k:<16} {v:>7,}")
    A("")
    real_pos = [m for m in manifest if m["class"] == "positive" and m["synthetic"] == "false"]
    A(f"  REAL positives (INMP441): {len(real_pos):,}"
      + ("  <-- the only honest detection evidence" if real_pos else "  <-- NONE"))
    A("")

    A("--- VOICE / SPEAKER DIVERSITY ---")
    voices = {m["voice_id"] for m in manifest if m["voice_id"]}
    pos_voices = {m["voice_id"] for m in manifest if m["class"] == "positive" and m["voice_id"]}
    spk = {m["speaker_id"] for m in manifest if m["speaker_id"]}
    A(f"  distinct voice_ids           {len(voices):,}")
    A(f"  distinct voices on POSITIVES {len(pos_voices):,}")
    A(f"  distinct human speaker_ids   {len(spk):,}")
    A("  NOTE: TTS voices are not speakers. No speaker-independence claim is possible.")
    A("")

    A("--- SOURCES & LICENCES ---")
    lic = defaultdict(Counter)
    for m in manifest:
        lic[m["source_corpus"]][m["source_license"]] += 1
    for corpus in sorted(lic):
        for lc, k in lic[corpus].items():
            A(f"  {corpus:<38} {lc:<34} {k:>7,}")
    A("")

    A("--- AUGMENTATION ---")
    aug = Counter(m["augmentation"] for m in manifest)
    for a, k in aug.most_common(10):
        A(f"  {a:<28} {k:>7,}  {100*k/n:5.1f}%")
    A("")

    A("--- LEVEL / SNR DISTRIBUTION ---")
    def dist(field, label):
        vals = []
        for m in manifest:
            try:
                v = float(m[field])
                if v == v:
                    vals.append(v)
            except (ValueError, TypeError):
                pass
        if not vals:
            A(f"  {label}: none"); return
        vals.sort()
        q = lambda p: vals[min(len(vals)-1, int(p*len(vals)))]
        A(f"  {label:<22} min {vals[0]:7.1f}  p25 {q(.25):7.1f}  med {q(.5):7.1f}"
          f"  p75 {q(.75):7.1f}  max {vals[-1]:7.1f}   n={len(vals):,}")
    dist("rms_dbfs", "RMS dBFS")
    dist("measured_snr_db", "measured SNR dB")
    dist("snr_db", "mixed-in SNR dB")
    A("")

    A("--- KEYWORD POSITION (positives) ---")
    on = [float(m["keyword_onset_ms"]) for m in manifest
          if m["class"] == "positive" and m["keyword_onset_ms"]]
    if on:
        on.sort()
        A(f"  onset ms   min {on[0]:.0f}  med {on[len(on)//2]:.0f}  max {on[-1]:.0f}   n={len(on):,}")
        A("  Spread is intentional: a centred corpus trains a model that fails on")
        A("  sliding windows. Offset sampling applies to every split.")
    A("")

    A("--- DUPLICATES & LEAKAGE ---")
    for k in ("hashes_crossing_splits", "duplicate_clips", "voices_crossing_splits",
              "speakers_crossing_splits", "utterances_crossing_splits",
              "synthetic_in_test", "synthetic_positives_in_test",
              "augmented_in_test", "test_size", "test_positives"):
        if k in stats:
            A(f"  {k:<34} {stats[k]}")
    if stats.get("declared_real_speaker_exception"):
        A(f"  declared exception (1 human speaker): {stats['declared_real_speaker_exception']}")
    A("")
    A("=" * 78)
    if fails:
        A(f"LEAKAGE: FAIL — {len(fails)} problem(s)")
        for f in fails:
            A(f"  - {f}")
    else:
        A("LEAKAGE: PASS — no leakage detected")
    A("=" * 78)
    return "\n".join(L)
