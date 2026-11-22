"""
Reward profiles: the small per-game description that tells the RL environment
which keys a game uses, where its score is kept, and when a game is over.

A "value spec" says where to read a number from the machine:
    {"source": "register", "index": 14}                  -> V[14]
    {"source": "memory", "address": 768}                 -> memory[768]
    {"source": "register", "index": 14, "divisor": 10, "modulus": 10}
                                                         -> the tens digit of V[14]
The optional divisor/modulus pick out one decimal digit, which is how many games
(including Pong) pack two scores into one number.
"""

import json
from pathlib import Path

KEY_NAMES = {
    "1": 0x1, "2": 0x2, "3": 0x3, "4": 0xC,
    "Q": 0x4, "W": 0x5, "E": 0x6, "R": 0xD,
    "A": 0x7, "S": 0x8, "D": 0x9, "F": 0xE,
    "Z": 0xA, "X": 0x0, "C": 0xB, "V": 0xF,
}

DEFAULTS = {
    "frame_skip": 4,            # the agent chooses an action every 4 frames
    "max_seconds": 120,         # safety limit on the length of one game
    "score_limit": None,        # end the game when either side reaches this score
    "end_on_wait_for_key": True,
    "death_penalty": 0.0,
    "hit_bonus": 0.0,           # reward for returning the ball (two-player ball games)
    "hit_bonus_limit": 3,       # at most this many hit bonuses per point
    "opponent": {"mode": "none"},
}


def read_value(machine, spec):
    """Read the number a value spec points at."""
    if spec["source"] == "register":
        raw = machine.V[spec["index"]]
    elif spec["source"] == "memory":
        raw = machine.memory[spec["address"] & 0xFFF]
    else:
        raise ValueError(f"Unknown value source: {spec['source']}")
    raw //= spec.get("divisor", 1)
    if "modulus" in spec:
        raw %= spec["modulus"]
    return raw


def value_range(spec):
    """How many different values a spec can take (used to handle wrap-around)."""
    if "modulus" in spec:
        return spec["modulus"]
    return 256 // spec.get("divisor", 1)


def change(old, new, spec):
    """The change from old to new, treating wrap-around (e.g. 255 -> 0) as a small step."""
    span = value_range(spec)
    d = (new - old) % span
    return d - span if d > span // 2 else d


def keys_to_numbers(names):
    """["1", "Q"] -> {0x1, 0x4}"""
    return {KEY_NAMES[name.upper()] for name in names}


def load_profile(path):
    with open(path, encoding="utf-8") as f:
        profile = json.load(f)
    merged = dict(DEFAULTS)
    merged.update(profile)
    return merged


def save_profile(profile, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
