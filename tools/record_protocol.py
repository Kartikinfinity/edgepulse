#!/usr/bin/env python3
"""Guided multi-condition recording session for real-device adaptation.

    python tools/record_protocol.py --session S_ADAPT_02
    python tools/record_protocol.py --session S_HELDOUT_01 --heldout
    python tools/record_protocol.py --session S_ADAPT_02 --only natural,soft

Why a protocol instead of "say it 100 times":

DOMAIN_GAP_ANALYSIS.md measured real and synthetic Takshila as 99.6% linearly
separable, unmoved by CMN or a different log floor. Real audio is therefore
required - but 100 identical takes buy 100 copies of ONE point in the space.
What the model needs is the SPREAD the device will actually meet: the same word
said quickly, slowly, softly, from further away.

Three kinds of take, and they are NOT interchangeable:

  positive   the keyword. Judged by the dataset factory's own acceptance rule.
  negative   speech that is NOT the keyword - near-homophones, partials,
             ordinary sentences. Judged for speech presence and level only; the
             keyword-span rule must never see these, because "shiksha" is
             supposed to fail it.
  ambient    VERIFIED SPEECH-FREE room audio. The take must be shown to contain
             no voice. This is what makes a false-alarm rate measurable, and
             EXP-007 could not report one because none of this exists yet.

Nothing here manufactures a negative by excising a keyword from a positive
recording. That is how EXP-007 produced a false-alarm figure of 1293/hour that
had to be withdrawn: the speech-span detector left most of a quiet keyword
behind, and true positives were counted as false accepts. Negatives are
RECORDED, never synthesised by deletion.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.paths import RECORDINGS_ROOT  # noqa: E402

KEYWORD = "Takshila"

# name, n, content, label, duration_ms, volume, pace, distance, say, why
POSITIVE_BLOCKS = [
    ("natural", 10, "keyword", "takshila", 3000, "normal", "normal", "0.3", KEYWORD,
     "the centre of the distribution - how the demo will actually be spoken"),
    ("slow", 6, "keyword", "takshila", 3000, "normal", "slow", "0.3", f"{KEYWORD} (drawn out)",
     "measured real spans reach 880 ms; the model must cover the long tail"),
    ("fast", 6, "keyword", "takshila", 3000, "normal", "fast", "0.3", f"{KEYWORD} (brisk)",
     "the 250 ms end of the admissible band, where takes get rejected"),
    ("soft", 6, "keyword", "takshila", 3000, "soft", "normal", "0.3",
     f"{KEYWORD} (quietly, not whispered)",
     "quiet speech is what clamps mel bins to the log floor - the failure mode"),
    ("loud", 5, "keyword", "takshila", 3000, "loud", "normal", "0.3",
     f"{KEYWORD} (clearly, projected)",
     "the top of the level range, and a check that nothing clips"),
    ("far", 6, "keyword", "takshila", 3000, "normal", "normal", "1.0", KEYWORD,
     "distance drops the speech band ~10 dB while the rumble floor stays put"),
    ("angled", 5, "keyword", "takshila", 3000, "normal", "normal", "0.5", KEYWORD,
     "off-axis, because nobody speaks straight into a breadboard"),
]

NEGATIVE_BLOCKS = [
    ("neg_ksha", 6, "speech", "neg_ksha", 3000, "normal", "normal", "0.3",
     "shiksha, raksha, lakshya, moksha (one per take)",
     "the ksha family - the phonetic core of Takshila in other words"),
    ("neg_taks", 6, "speech", "neg_taks", 3000, "normal", "normal", "0.3",
     "taxi, tax, tactical, taxonomy (one per take)",
     "the /taeks/ onset family"),
    ("neg_partial", 4, "speech", "neg_partial", 3000, "normal", "normal", "0.3",
     "'taksh...' then stop, and 'shila' alone",
     "partial keywords - the sliding-window failure mode, from a real mouth"),
    ("neg_speech", 8, "speech", "neg_speech", 4000, "normal", "normal", "0.3",
     "any ordinary sentence, different each take",
     "general speech on this microphone, to anchor the negative class in-domain"),
]

# Long takes: an FA/hour figure needs MINUTES, and 3 s at a time will not get
# there. 12 x 60 s = 12 minutes. Seeing zero false accepts in 12 minutes bounds
# the rate at roughly 15/hour (Poisson rule of three); that is the resolution
# this buys, and it is stated rather than implied.
AMBIENT_BLOCKS = [
    ("amb_quiet", 6, "ambient", "ambient_quiet", 60000, "none", "none", "-",
     "NOTHING - stay completely silent, do not leave the room",
     "the demo's resting state; every false accept here is one the judges see"),
    ("amb_active", 6, "ambient", "ambient_active", 60000, "none", "none", "-",
     "NOTHING vocal - typing, papers, a chair, a door, footsteps are all WANTED",
     "impulsive room events are realistic negatives and are deliberately kept"),
]


def run_block(spec, args) -> tuple[int, str]:
    name, n, content, label, dur, vol, pace, dist, say, why = spec
    print("\n" + "=" * 74)
    print(f"BLOCK {name}   {n} takes x {dur/1000:.0f}s   content={content}")
    if content == "ambient":
        print(f"  DO:   {say}")
    else:
        print(f"  SAY:  {say}")
    print(f"  WHY:  {why}")
    print("=" * 74)
    if not args.yes:
        try:
            r = input("  [Enter] start, 's' skip, 'q' quit: ").strip().lower()
        except EOFError:
            r = ""
        if r == "s":
            print("  skipped")
            return 0, name
        if r == "q":
            raise SystemExit("stopped by operator")

    cmd = [sys.executable, str(ROOT / "tools" / "record_session.py"),
           "--record", label, "--content", content,
           "--repeat", str(n), "--duration", str(dur),
           "--speaker", args.speaker, "--session", args.session,
           "--environment", args.environment,
           "--notes", f"protocol_block={name}"]
    if content != "ambient":
        cmd += ["--volume", vol, "--rate-label", pace, "--distance", dist]
    else:
        # No countdown: a spoken "3, 2, 1" would put the operator's voice in a
        # take whose entire purpose is to contain none.
        cmd += ["--no-prompt"]
    if args.port:
        cmd += ["--port", args.port]
    return subprocess.call(cmd), name


def write_session_marker(args, blocks) -> Path:
    """Record the session's role on disk, at capture time.

    The held-out session is the whole basis of the session-disjoint control. If
    its identity lives only in a person's memory or in a config edit made later,
    it will eventually be trained on by accident. Writing it beside the audio
    means the factory and the audit can both see it without being told.
    """
    outdir = RECORDINGS_ROOT / args.speaker / args.session
    outdir.mkdir(parents=True, exist_ok=True)
    marker = outdir / "_session.json"
    payload = {
        "session_id": args.session,
        "speaker_id": args.speaker,
        "role": "heldout_test" if args.heldout else "adaptation_train",
        "quarantined": bool(args.heldout),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "environment": args.environment,
        "keyword": KEYWORD,
        "protocol_blocks": [b[0] for b in blocks],
        "note": ("THIS SESSION IS TEST-ONLY. It must not appear in train or "
                 "validation; the leakage gate fails the build if it does."
                 if args.heldout else
                 "Adaptation material: may enter train/validation."),
    }
    marker.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return marker


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", required=True,
                    help="session name; it becomes the provenance key and the "
                         "unit of the session-disjoint split")
    ap.add_argument("--speaker", default="SPK_PILOT_01",
                    help="keep this STABLE across sessions - one person is one "
                         "speaker_id regardless of directory")
    ap.add_argument("--environment", default="E1")
    ap.add_argument("--port")
    ap.add_argument("--heldout", action="store_true",
                    help="this session is TEST ONLY; writes a quarantine marker")
    ap.add_argument("--only", default="", help="comma-separated block names")
    ap.add_argument("--positives-only", action="store_true")
    ap.add_argument("--negatives-only", action="store_true",
                    help="only the speech-negative and ambient blocks")
    ap.add_argument("--yes", action="store_true", help="no prompt between blocks")
    args = ap.parse_args()

    if args.positives_only and args.negatives_only:
        raise SystemExit("--positives-only and --negatives-only are exclusive")
    blocks: list = []
    if not args.negatives_only:
        blocks += POSITIVE_BLOCKS
    if not args.positives_only:
        blocks += NEGATIVE_BLOCKS + AMBIENT_BLOCKS
    if args.only:
        want = {b.strip() for b in args.only.split(",")}
        blocks = [b for b in blocks if b[0] in want]
        if not blocks:
            raise SystemExit(f"no block matches {sorted(want)}")

    secs = sum(b[1] * (b[4] / 1000.0 + 4) for b in blocks)
    print("=" * 74)
    print(f"RECORDING PROTOCOL - session {args.session}")
    print("=" * 74)
    print(f"  {len(blocks)} blocks, {sum(b[1] for b in blocks)} takes, "
          f"roughly {secs/60:.0f} minutes including pauses")
    marker = write_session_marker(args, blocks)
    print(f"  wrote {marker.relative_to(ROOT)}")
    if args.heldout:
        print("\n  *** HELD-OUT SESSION - TEST ONLY ***")
        print("  Nothing recorded here may enter train or validation. The marker")
        print("  above records that, and the leakage gate enforces it.")

    print("\n  Before you start:")
    print("   - speak ACROSS the microphone, not into it")
    print("   - keep the board still; handling noise is the loudest thing it hears")
    print("   - a take rejected as TOO QUIET means move closer, not speak harder")
    print("   - ambient blocks: no countdown, no talking, do not leave the room")

    rc = 0
    ran = []
    for b in blocks:
        code, name = run_block(b, args)
        rc |= code
        ran.append(name)

    print("\n" + "=" * 74)
    print("PROTOCOL COMPLETE")
    print("=" * 74)
    print("Check what you actually got before recording more:")
    print(f"  python tools/audit_recordings.py")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
