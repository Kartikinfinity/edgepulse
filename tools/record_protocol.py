#!/usr/bin/env python3
"""Guided multi-condition recording session for real-device adaptation.

    python tools/record_protocol.py --session S_ADAPT_01
    python tools/record_protocol.py --session S_HELDOUT_01 --heldout
    python tools/record_protocol.py --session S_ADAPT_01 --only natural,soft

Why a protocol instead of "say it 100 times":

DOMAIN_GAP_ANALYSIS.md measured real and synthetic Takshila as 99.6% linearly
separable, unmoved by CMN or a different log floor. Real audio is therefore
required - but 100 identical takes buy 100 copies of ONE point in the space.
What the model needs is the SPREAD the device will actually meet: the same word
said quickly, slowly, softly, from further away.

It also asks for real NEGATIVE speech from the same mouth and microphone. The
near-homophones that attack this keyword - the क्ष family and the /taeks/ family
- currently exist only as TTS. A false accept on the demo stage will come from
this speaker's voice, so the hardest negatives should come from it too.

Each block calls tools/record_session.py, which applies the dataset factory's
own acceptance rule at capture time and says why a take was rejected. Level is
the binding data-quality constraint (20.7% of mel bins on the log floor against
8.3% for synthetic), so "TOO QUIET" is the message to watch for.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

KEYWORD = "Takshila"

# (block, n, volume, rate, distance_m, what to say, why it is here)
POSITIVE_BLOCKS = [
    ("natural", 10, "normal", "normal", "0.3", KEYWORD,
     "the centre of the distribution - how the demo will actually be spoken"),
    ("slow", 6, "normal", "slow", "0.3", f"{KEYWORD} (drawn out)",
     "measured real spans reach 880 ms; the model must cover the long tail"),
    ("fast", 6, "normal", "fast", "0.3", f"{KEYWORD} (brisk)",
     "the 250 ms end of the admissible band, where takes get rejected"),
    ("soft", 6, "soft", "normal", "0.3", f"{KEYWORD} (quietly, not whispered)",
     "quiet speech is what clamps mel bins to the log floor - the failure mode"),
    ("loud", 5, "loud", "normal", "0.3", f"{KEYWORD} (clearly, projected)",
     "the top of the level range, and a check that nothing clips"),
    ("far", 6, "normal", "normal", "1.0", KEYWORD,
     "distance drops the speech band ~10 dB while the rumble floor stays put"),
    ("angled", 5, "normal", "normal", "0.5", KEYWORD,
     "off-axis, because nobody speaks straight into a breadboard"),
]

# Real negatives from the same speaker and microphone.
NEGATIVE_BLOCKS = [
    ("neg_ksha", 6, "normal", "normal", "0.3",
     "shiksha, raksha, lakshya, moksha (one per take)",
     "the क्ष family - the phonetic core of Takshila in other words"),
    ("neg_taks", 6, "normal", "normal", "0.3",
     "taxi, tax, tactical, taxonomy (one per take)",
     "the /taeks/ onset family"),
    ("neg_partial", 4, "normal", "normal", "0.3",
     "'taksh...' then stop, and 'shila' alone",
     "partial keywords - the sliding-window failure mode, from a real mouth"),
    ("neg_speech", 6, "normal", "normal", "0.3",
     "any ordinary sentence, different each take",
     "general speech on this microphone, to anchor the negative class in-domain"),
]


def run_block(block, n, vol, rate, dist, say, why, args) -> int:
    print("\n" + "=" * 74)
    print(f"BLOCK {block}   {n} takes   volume={vol}  pace={rate}  distance={dist} m")
    print(f"  SAY:  {say}")
    print(f"  WHY:  {why}")
    print("=" * 74)
    if not args.yes:
        try:
            r = input("  [Enter] to start this block, 's' to skip, 'q' to quit: ").strip().lower()
        except EOFError:
            r = ""
        if r == "s":
            print("  skipped")
            return 0
        if r == "q":
            raise SystemExit("stopped by operator")

    cmd = [sys.executable, str(ROOT / "tools" / "record_session.py"),
           "--record", f"{KEYWORD.lower() if not block.startswith('neg') else block}",
           "--repeat", str(n), "--duration", str(args.duration),
           "--speaker", args.speaker, "--session", args.session,
           "--volume", vol, "--rate-label", rate, "--distance", dist,
           "--environment", args.environment,
           "--notes", f"protocol_block={block}"]
    if args.port:
        cmd += ["--port", args.port]
    if block.startswith("neg"):
        # A negative take holds speech but not the keyword, so the factory's
        # keyword-span rule must not be used to accept or reject it.
        cmd += ["--no-expect-speech"] if "--no-expect-speech" in _recorder_flags() else []
    return subprocess.call(cmd)


def _recorder_flags() -> str:
    try:
        return (ROOT / "tools" / "record_session.py").read_text(encoding="utf-8")
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", required=True,
                    help="session name; it becomes the provenance key and the "
                         "unit of the session-disjoint split")
    ap.add_argument("--speaker", default="SPK_PILOT_01")
    ap.add_argument("--environment", default="E1")
    ap.add_argument("--duration", type=int, default=3000)
    ap.add_argument("--port")
    ap.add_argument("--heldout", action="store_true",
                    help="this session is destined for TEST ONLY; print the "
                         "quarantine reminder and skip nothing")
    ap.add_argument("--only", default="",
                    help="comma-separated block names to run")
    ap.add_argument("--positives-only", action="store_true")
    ap.add_argument("--yes", action="store_true", help="no prompt between blocks")
    args = ap.parse_args()

    blocks = list(POSITIVE_BLOCKS)
    if not args.positives_only:
        blocks += NEGATIVE_BLOCKS
    if args.only:
        want = {b.strip() for b in args.only.split(",")}
        blocks = [b for b in blocks if b[0] in want]
        if not blocks:
            raise SystemExit(f"no block matches {sorted(want)}")

    total = sum(b[1] for b in blocks)
    print("=" * 74)
    print(f"RECORDING PROTOCOL - session {args.session}")
    print("=" * 74)
    print(f"  {len(blocks)} blocks, {total} takes, roughly {total * 15 // 60} minutes")
    if args.heldout:
        print("\n  *** HELD-OUT SESSION ***")
        print("  Everything recorded here goes to TEST and nothing else. Do not")
        print("  record training material in this session - the session is the")
        print("  unit of the disjointness control, and mixing breaks it.")
    print("\n  Before you start:")
    print("   - speak across the microphone, not into it")
    print("   - keep the board still; handling noise is the loudest thing it hears")
    print("   - wait for the countdown, then say the word once")
    print("   - a take rejected as TOO QUIET means move closer, not speak harder")

    rc = 0
    for b in blocks:
        rc |= run_block(*b, args)

    print("\n" + "=" * 74)
    print("PROTOCOL COMPLETE")
    print("=" * 74)
    print("Next:")
    print(f"  python tools/audio_qc.py data/recordings/{args.speaker}/{args.session}")
    print("  python tools/build_dataset.py --out data/dataset_v4 --force")
    if args.heldout:
        print(f"\n  Then set REAL_HELDOUT_SESSION = \"{args.session}\" in")
        print("  tools/dataset_factory/config.py so this session is quarantined.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
