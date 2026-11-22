"""
Opponents for two-player games. An opponent is anything that, once per frame,
returns the set of CHIP-8 keys it is holding down.
"""

import random

from .profiles import keys_to_numbers, read_value


class NoOpponent:
    """For one-player games: never presses anything."""

    def reset(self):
        pass

    def keys(self, machine):
        return set()


class TrackingOpponent:
    """
    A simple rule-based player: move the paddle towards the ball.

    skill (0 to 1) is the chance it reacts on any given frame, so lower skill means a
    slower, beatable opponent. Needs "ball_y" and "paddle_y" value specs in the profile.
    """

    def __init__(self, config, seed=None):
        self.ball_y = config["ball_y"]
        self.paddle_y = config["paddle_y"]
        self.paddle_offset = config.get("paddle_center_offset", 0)
        self.skill = config.get("skill", 0.6)
        self.up = keys_to_numbers(config["keys"]["up"])
        self.down = keys_to_numbers(config["keys"]["down"])
        self.random = random.Random(seed)

    def reset(self):
        pass

    def keys(self, machine):
        if self.random.random() > self.skill:
            return set()                       # didn't react this frame
        ball = read_value(machine, self.ball_y)
        paddle = read_value(machine, self.paddle_y) + self.paddle_offset
        if ball < paddle - 1:
            return self.up
        if ball > paddle + 1:
            return self.down
        return set()


def make_opponent(config, seed=None):
    mode = config.get("mode", "none")
    if mode == "none":
        return NoOpponent()
    if mode == "scripted":
        return TrackingOpponent(config, seed)
    raise ValueError(f"Unknown opponent mode: {mode}")
