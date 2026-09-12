#!/usr/bin/env python3
"""What real-device audio actually exists, and what is still missing.

    python tools/audit_recordings.py
    python tools/audit_recordings.py --dataset data/dataset_v3
    python tools/audit_recordings.py --json

Answers, per session and per role (adaptation vs held-out):
  speakers, sessions, positives, VERIFIED negatives, rejects and why,
  level distribution, duplicate/near-duplicate contamination, and whether any
  source recording appears in more than one dataset split.

The counts here are the gate on whether a model claim is worth making. EXP-007
produced 14/15 held-out detections on 3 utterances and could not report a
real-device false-alarm rate at all, because no speech-free device audio
existed. This tool exists so that gap is visible before training, not after.

Read-only. It builds nothing and changes nothing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import wave
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.paths import DATASET_ROOT, PROJECT_ROOT, RECORDINGS_ROOT  # noqa: E402

# Targets, and where each number comes from.
TARGET_ADAPT_POSITIVES = 60      # ~15 usable/condition across 7 conditions
TARGET_HELDOUT_POSITIVES = 40    # +-15 pp on recall (Wilson); 18 gives +-35 pp
TARGET_HELDOUT_NEG_SPEECH = 20   # near-homophones + partials + sentences
TARGET_AMBIENT_MINUTES = 12.0    # 0 FA in 12 min bounds the rate at ~15/hour


def load_check():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "rs", str(PROJECT_ROOT / "tools" / "record_session.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def content_of(path: Path) -> str:
    """What a take was recorded AS. The sidecar is authoritative; the filename
    is the fallback for takes recorded before --content existed."""
    j = path.with_suffix(".json")
    if j.is_file():
        try:
            d = json.loads(j.read_text(encoding="utf-8"))
            c = d.get("capture_stats", {}).get("content_kind")
            if c:
                return c
        except Exception:
            pass
    n = path.name.lower()
    if any(t in n for t in ("ambient", "silence", "roomtone", "noise")):
        return "ambient"
    if "_neg_" in n or n.startswith("neg_"):
        return "speech"
    return "keyword"


def session_role(sess_dir: Path) -> str:
    m = sess_dir / "_session.json"
    if m.is_file():
        try:
            return json.loads(m.read_text(encoding="utf-8")).get("role", "unmarked")
        except Exception:
            pass
    return "unmarked"


def audit_recordings(rs) -> dict:
    sessions: dict[str, dict] = {}
    for wav in sorted(RECORDINGS_ROOT.rglob("*.wav")):
        sess_dir = wav.parent
        sid = sess_dir.name
        s = sessions.setdefault(sid, {
            "session_id": sid, "speaker_dir": sess_dir.parent.name,
            "role": session_role(sess_dir), "path": str(sess_dir),
            "takes": [], "seconds": 0.0,
        })
        with wave.open(str(wav), "rb") as w:
            n, sr = w.getnframes(), w.getframerate()
            raw = w.readframes(n)
        kind = content_of(wav)
        chk = rs.speech_check(raw, kind)
        x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
        s["seconds"] += n / float(sr or 16000)
        s["takes"].append({
            "file": wav.name, "content": kind,
            "accepted": bool(chk["usable"]), "reason": chk["reason"],
            "seconds": n / float(sr or 16000),
            "peak_dbfs": float(20 * np.log10(np.abs(x).max() + 1e-12)),
            "band_peak_db": chk.get("band_peak_db"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "fingerprint": fingerprint(x, sr or 16000),
        })
    return sessions


def near_duplicates(sessions: dict, thresh: float = 0.995):
    """Exact duplicates by hash, near-duplicates by AUDIO CONTENT.

    An earlier version keyed on (duration, peak dBFS). Every take is 3.000 s, so
    that was really matching peak level alone, and it flagged three pairs of
    unrelated takes from different sessions on different days. Coincidence, not
    contamination - and a contamination checker that cries wolf is worse than
    none, because the real one gets ignored.

    This compares a content fingerprint: 16 mel bands x 8 time slices, mean-
    removed, cosine similarity. Two copies of one file score 1.0; two genuine
    takes of the same word by the same speaker score well below the threshold.
    """
    exact, near = [], []
    seen: dict[str, str] = {}
    tags: list[str] = []
    rows: list[np.ndarray] = []
    for s in sessions.values():
        for t in s["takes"]:
            tag = f"{s['session_id']}/{t['file']}"
            if t["sha256"] in seen:
                exact.append((seen[t["sha256"]], tag, 1.0))
                continue
            seen[t["sha256"]] = tag
            fp = t.get("fingerprint")
            if fp is not None:
                tags.append(tag)
                rows.append(np.asarray(fp, dtype=np.float64))
    if len(rows) < 2:
        return exact, near
    M = np.vstack(rows)
    # Every take shares the same microphone, room and rumble signature, so raw
    # fingerprints correlate at >0.995 across the board - silence against
    # speech included. Removing the corpus mean leaves only what DISTINGUISHES
    # a take, which is the thing a duplicate check should be looking at.
    M = M - M.mean(axis=0, keepdims=True)
    norms = np.linalg.norm(M, axis=1, keepdims=True)
    M = M / np.maximum(norms, 1e-12)
    S = M @ M.T
    for i in range(len(tags)):
        for j in range(i + 1, len(tags)):
            if S[i, j] >= thresh:
                near.append((tags[i], tags[j], round(float(S[i, j]), 4)))
    return exact, near


def fingerprint(x: np.ndarray, sr: int) -> list[float]:
    """16 mel-ish bands x 8 time slices, mean-removed. Cheap and content-based."""
    n = min(x.size, sr * 30)
    x = x[:n]
    if n < 1024:
        return [0.0] * 128
    slices = np.array_split(x, 8)
    out = []
    for sl in slices:
        sp = np.abs(np.fft.rfft(sl * np.hanning(sl.size)))
        edges = np.linspace(0, sp.size, 17).astype(int)
        out += [float(np.log(sp[edges[k]:edges[k + 1]].mean() + 1e-12))
                for k in range(16)]
    v = np.asarray(out)
    return (v - v.mean()).tolist()


def dataset_split_check(dataset: Path) -> dict:
    """Does any recording session appear in more than one dataset split?"""
    out = {"dataset": str(dataset), "available": False}
    mdir = dataset / "manifests"
    if not mdir.is_dir():
        return out
    out["available"] = True
    sess = defaultdict(set)
    spk = defaultdict(set)
    hashes = defaultdict(set)
    for split in ("train", "validation", "test"):
        p = mdir / f"{split}.csv"
        if not p.is_file():
            continue
        with p.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("session_id"):
                    sess[r["session_id"]].add(split)
                if r.get("synthetic") == "false" and r.get("speaker_id"):
                    spk[r["speaker_id"]].add(split)
                hashes[r["sha256"]].add(split)
    out["sessions_by_split"] = {k: sorted(v) for k, v in sorted(sess.items())}
    # An adaptation session spanning train+validation is BY DESIGN - the split
    # is utterance-disjoint within it. The control that matters is that a
    # session used for test appears nowhere else.
    out["heldout_sessions"] = sorted(k for k, v in sess.items() if "test" in v)
    out["heldout_leaking"] = {k: sorted(v) for k, v in sess.items()
                              if "test" in v and len(v) > 1}
    out["sessions_in_multiple_splits"] = {k: sorted(v) for k, v in sess.items()
                                          if len(v) > 1}
    out["real_speakers_by_split"] = {k: sorted(v) for k, v in sorted(spk.items())}
    out["clips_crossing_splits"] = sum(1 for v in hashes.values() if len(v) > 1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=DATASET_ROOT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rs = load_check()
    sessions = audit_recordings(rs)
    exact, near = near_duplicates(sessions)
    splits = dataset_split_check(args.dataset)

    roles = defaultdict(list)
    for s in sessions.values():
        roles[s["role"]].append(s)

    def tally(takes, kind):
        sel = [t for t in takes if t["content"] == kind]
        return sum(1 for t in sel if t["accepted"]), len(sel)

    totals = {"pos": 0, "neg": 0, "amb_sec": 0.0, "amb_takes": 0}

    print("=" * 78)
    print("REAL-DEVICE RECORDING AUDIT")
    print("=" * 78)
    print(f"  recordings root : {RECORDINGS_ROOT}")
    print(f"  dataset         : {args.dataset}")

    for role in ("heldout_test", "adaptation_train", "unmarked"):
        if role not in roles:
            continue
        print(f"\n{'-' * 78}\nROLE: {role}")
        for s in sorted(roles[role], key=lambda z: z["session_id"]):
            pa, pn = tally(s["takes"], "keyword")
            na, nn = tally(s["takes"], "speech")
            aa, an = tally(s["takes"], "ambient")
            amb_sec = sum(t["seconds"] for t in s["takes"]
                          if t["content"] == "ambient" and t["accepted"])
            totals["pos"] += pa
            totals["neg"] += na
            totals["amb_sec"] += amb_sec
            totals["amb_takes"] += aa
            print(f"\n  {s['session_id']}   speaker dir '{s['speaker_dir']}'   "
                  f"{len(s['takes'])} takes, {s['seconds']/60:.1f} min")
            print(f"    positives (keyword)      {pa:>3}/{pn:<4} accepted")
            print(f"    negatives (real speech)  {na:>3}/{nn:<4} accepted")
            print(f"    ambient (speech-free)    {aa:>3}/{an:<4} accepted "
                  f"= {amb_sec/60:.1f} min")
            rej = Counter(t["reason"].split(" (")[0].split(" - ")[0]
                          for t in s["takes"] if not t["accepted"])
            if rej:
                print("    rejected:")
                for r, c in rej.most_common():
                    print(f"      {c:>3}x  {r}")
            lv = [t["band_peak_db"] for t in s["takes"]
                  if t["content"] != "ambient" and t["band_peak_db"] is not None]
            if lv:
                lv = np.asarray(lv)
                print(f"    speech-band peak dB      med {np.median(lv):6.1f}  "
                      f"p10 {np.percentile(lv,10):6.1f}  p90 {np.percentile(lv,90):6.1f}"
                      f"   (want > {rs.LEVEL_TARGET_DB:.0f})")

    print(f"\n{'-' * 78}\nCONTAMINATION")
    print(f"  exact duplicate audio files      {len(exact)}")
    for a, b, _ in exact[:5]:
        print(f"    {a}  ==  {b}")
    print(f"  suspected near-duplicates        {len(near)}")
    for a, b, _ in near[:5]:
        print(f"    {a}  ~~  {b}")
    if splits["available"]:
        bad = splits["heldout_leaking"]
        print(f"  held-out session leaking out of test {len(bad)}"
              f"{'  <-- LEAK' if bad else '   OK'}")
        for k, v in bad.items():
            print(f"    {k}: {'+'.join(v)}")
        multi = {k: v for k, v in splits["sessions_in_multiple_splits"].items()
                 if k not in bad}
        if multi:
            print("  adaptation sessions spanning train/validation (by design):")
            for k, v in multi.items():
                print(f"    {k}: {'+'.join(v)}")
        print(f"  identical clips across splits    {splits['clips_crossing_splits']}")
        print("  session -> split:")
        for k, v in splits["sessions_by_split"].items():
            print(f"    {k:<22} {'+'.join(v)}")
    else:
        print(f"  dataset manifests not found at {args.dataset}")

    print(f"\n{'-' * 78}\nAGAINST TARGET")
    heldout_pos = sum(tally(s["takes"], "keyword")[0]
                      for s in roles.get("heldout_test", []))
    heldout_neg = sum(tally(s["takes"], "speech")[0]
                      for s in roles.get("heldout_test", []))
    adapt_pos = totals["pos"] - heldout_pos
    rows = [
        ("adaptation positives", adapt_pos, TARGET_ADAPT_POSITIVES),
        ("held-out positives", heldout_pos, TARGET_HELDOUT_POSITIVES),
        ("held-out negative speech", heldout_neg, TARGET_HELDOUT_NEG_SPEECH),
        ("speech-free ambient (min)", round(totals["amb_sec"] / 60, 1),
         TARGET_AMBIENT_MINUTES),
    ]
    print(f"  {'item':<30}{'have':>8}{'target':>9}{'missing':>10}")
    for name, have, want in rows:
        miss = max(0, round(want - have, 1))
        print(f"  {name:<30}{have:>8}{want:>9}{miss:>10}"
              f"{'   OK' if miss == 0 else ''}")

    if args.json:
        out = {"sessions": sessions, "exact_duplicates": exact,
               "near_duplicates": near, "splits": splits, "targets": rows}
        p = PROJECT_ROOT / "artifacts" / "recording_audit.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
