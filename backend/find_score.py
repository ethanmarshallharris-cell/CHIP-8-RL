"""
Find where a game keeps its score, and save the results to find_score_log.txt.

Plays the ROM for two minutes of game time with random key presses, then lists the
numbers that behaved most like a score.

Example (from the backend folder):
    python find_score.py storage\\roms\\1db31d734b9352f9.ch8 --keys 1 Q 4 R
"""

import argparse
from datetime import datetime
from pathlib import Path

from rl.finder import describe, find_score_candidates
from rl.profiles import keys_to_numbers

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Find a CHIP-8 game's score.")
    parser.add_argument("rom")
    parser.add_argument("--keys", nargs="+", required=True,
                        help="laptop keys the game uses, e.g. 1 Q 4 R")
    parser.add_argument("--seconds", type=int, default=120)
    args = parser.parse_args()

    rom = Path(args.rom).read_bytes()
    keys = sorted(keys_to_numbers(args.keys))
    results = find_score_candidates(rom, keys, seconds=args.seconds)

    lines = [f"Score finder - {Path(args.rom).name} - {datetime.now():%Y-%m-%d %H:%M:%S}",
             f"Played {args.seconds} s with random presses of: {' '.join(args.keys)}", ""]
    if not results:
        lines.append("No score-like numbers found. Try more keys or a longer --seconds.")
    for rank, r in enumerate(results[:10], start=1):
        values = " -> ".join(str(v) for v in r["values"])
        lines.append(f"{rank:>2}. {describe(r['spec'])}")
        lines.append(f"    values seen: {values}")
        lines.append(f"    profile spec: {r['spec']}")
    report = "\n".join(lines)
    print(report)
    (HERE / "find_score_log.txt").write_text(report + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
