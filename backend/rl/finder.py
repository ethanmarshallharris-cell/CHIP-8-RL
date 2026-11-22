"""
The score finder: plays a game with random key presses and looks for numbers that
behave like a score - they change rarely, in small steps, and mostly go up.

It looks in two places:
  1. Numbers the game displays with FX33 (and each of their decimal digits) - the best clue.
  2. Every register and memory byte - the fallback "memory search".
"""

import random

from chip8 import Chip8

from .profiles import change


def candidate_specs(machine):
    """Every place a score might live, as value specs."""
    specs = []
    for address, (reg, _) in sorted(machine.displayed_numbers.items()):
        base = {"source": "register", "index": reg, "shown_by_fx33_at": address}
        specs.append(dict(base))
        specs.append(dict(base, divisor=100, modulus=10, digit="hundreds"))
        specs.append(dict(base, divisor=10, modulus=10, digit="tens"))
        specs.append(dict(base, modulus=10, digit="ones"))
    for i in range(16):
        specs.append({"source": "register", "index": i})
    for address in range(0x200, 0x1000):
        specs.append({"source": "memory", "address": address})
    return specs


def _read(machine, spec):
    raw = machine.V[spec["index"]] if spec["source"] == "register" else machine.memory[spec["address"]]
    raw //= spec.get("divisor", 1)
    return raw % spec["modulus"] if "modulus" in spec else raw


def find_score_candidates(rom_bytes, keys, seconds=120, seed=0, hold_frames=8):
    """
    Play the ROM for `seconds` of game time, pressing random combinations of `keys`
    (a list of CHIP-8 key numbers), and return the most score-like value specs, best first.
    """
    rng = random.Random(seed)
    machine = Chip8(seed=seed)
    machine.load_rom(rom_bytes)

    # Warm up so the game has drawn its score at least once and FX33 sites are known.
    for _ in range(60):
        machine.run_frame()

    specs = candidate_specs(machine)
    stats = [{"ups": 0, "downs": 0, "big": 0, "history": [_read(machine, s)]} for s in specs]
    pressed = set()

    for frame in range(int(seconds * 60)):
        if frame % hold_frames == 0:
            pressed = {k for k in keys if rng.random() < 0.5}
        machine.set_keys(pressed)
        machine.run_frame()
        for spec, st in zip(specs, stats):
            new = _read(machine, spec)
            old = st["history"][-1]
            if new != old:
                d = change(old, new, spec) if "modulus" in spec else new - old
                if d == 1:
                    st["ups"] += 1
                elif d < 0:
                    st["downs"] += 1
                else:
                    st["big"] += 1
                st["history"].append(new)

    results = []
    for spec, st in zip(specs, stats):
        changes = st["ups"] + st["downs"] + st["big"]
        if st["ups"] == 0:
            continue
        # A score goes up by 1 at a time, rarely, and (almost) never down.
        rate = changes / seconds
        score = st["ups"] - 3 * st["downs"] - 2 * st["big"]
        if rate > 1.0:          # changes more than once a second: probably a position or timer
            score -= 10 * rate
        if "shown_by_fx33_at" in spec:
            score += 2          # displayed numbers are the strongest clue
        if "digit" in spec:
            score += 1          # a single digit is a cleaner signal than a combined number
        if score > 0:
            results.append({"spec": spec, "score": score, "values": st["history"][:12]})
    results.sort(key=lambda r: -r["score"])
    return results


def describe(spec):
    if spec["source"] == "register":
        where = f"V{spec['index']:X}"
    else:
        where = f"memory[0x{spec['address']:03X}]"
    if "digit" in spec:
        where = f"{spec['digit']} digit of {where}"
    if "shown_by_fx33_at" in spec:
        where += f" (displayed by FX33 at 0x{spec['shown_by_fx33_at']:03X})"
    return where
