"""
Tests for the RL environment and score finder.

These use a tiny made-up "game" instead of a real ROM: every time key 5 is released,
the score in V3 goes up by one and is displayed with FX33. When the score reaches 3,
the game waits for a key (game over).
"""

import pytest

pytest.importorskip("gymnasium")

from gymnasium.utils.env_checker import check_env

from rl.env import Chip8Env
from rl.finder import find_score_candidates
from rl.profiles import DEFAULTS, change

# 200: V3 = 0
# 202: I = 0x300 ; 204: FX33 on V3 (display the score)
# 206: V0 = 5 ; 208: skip next if key 5 NOT pressed -> 20A: jump 210 (pressed) / 20C: jump 202
# 210: wait until key 5 is not pressed: skip if not pressed (EXA1) -> 212 jump 210 / 214 add 1
# 214: V3 += 1 ; 216: if V3 == 3 skip -> 218 jump 202 / 21A: FX0A wait (game over)
TOY_GAME = bytes.fromhex(
    "6300 A300 F333 6005 E0A1 1210 1202 0000 E0A1 1210 7301 3303 1202 F10A 121A"
)

PROFILE = dict(DEFAULTS, **{
    "actions": {"wait": [], "press": ["W"]},       # laptop W = CHIP-8 key 5
    "score": {"source": "register", "index": 3},
    "max_seconds": 10,
})


def test_environment_follows_the_gym_rules():
    check_env(Chip8Env(TOY_GAME, PROFILE, seed=0), skip_render_check=True)


def test_scoring_gives_reward_and_game_over_ends_the_episode():
    env = Chip8Env(TOY_GAME, PROFILE, seed=0)
    obs, _ = env.reset(seed=0)
    assert obs.shape == (4, 32, 64)
    total = 0.0
    for step in range(100):
        action = 1 if step % 2 == 0 else 0          # press, release, press, release...
        obs, reward, terminated, truncated, info = env.step(action)
        total += reward
        if terminated:
            break
    assert terminated and total == 3 and info["scores"]["agent"] == 3


def test_time_limit_truncates():
    env = Chip8Env(TOY_GAME, PROFILE, seed=0)
    env.reset(seed=0)
    for _ in range(env.max_steps):
        _, _, terminated, truncated, _ = env.step(0)   # never press: never score
    assert truncated and not terminated


def test_score_finder_finds_the_displayed_score():
    results = find_score_candidates(TOY_GAME, keys=[0x5], seconds=20)
    best = results[0]["spec"]
    assert best["source"] == "register" and best["index"] == 3 and "shown_by_fx33_at" in best


def test_wrap_around_counts_as_a_small_step():
    assert change(255, 0, {"source": "register", "index": 0}) == 1
    assert change(9, 0, {"source": "register", "index": 0, "modulus": 10}) == 1
