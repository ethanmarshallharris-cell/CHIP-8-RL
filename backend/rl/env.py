"""
The Gymnasium environment: wraps the CHIP-8 core so an RL agent can play it.

Each step the agent picks one action (e.g. "up"), the environment holds the matching
keys for frame_skip frames, and returns:
    observation - the last 4 screens, shape (4, 32, 64), pixels 0 or 255
    reward      - from the reward profile (score changes, penalties, bonuses)
    terminated  - the game ended (score limit reached, lives gone, waiting for a key)
    truncated   - the time limit was reached
"""

from collections import deque

import gymnasium as gym
import numpy as np

from chip8 import Chip8, HEIGHT, WIDTH

from .opponents import make_opponent
from .profiles import change, keys_to_numbers, read_value

STACK = 4


class Chip8Env(gym.Env):
    metadata = {"render_modes": ["rgb_array"]}

    def __init__(self, rom_bytes, profile, seed=None):
        super().__init__()
        self.rom = bytes(rom_bytes)
        self.profile = profile
        self.frame_skip = profile["frame_skip"]
        self.max_steps = int(profile["max_seconds"] * 60 / self.frame_skip)

        self.action_names = list(profile["actions"].keys())
        self.action_keys = [keys_to_numbers(k) for k in profile["actions"].values()]
        self.action_space = gym.spaces.Discrete(len(self.action_names))
        self.observation_space = gym.spaces.Box(0, 255, (STACK, HEIGHT, WIDTH), dtype=np.uint8)

        self.machine = Chip8(seed=seed)
        self.machine.load_rom(self.rom)
        self.opponent = make_opponent(profile["opponent"], seed)
        self.frames = deque(maxlen=STACK)

    # -------------------------------------------------------------- helpers
    def _screen(self):
        return np.frombuffer(bytes(self.machine.screen), dtype=np.uint8).reshape(HEIGHT, WIDTH) * 255

    def _observation(self):
        return np.stack(self.frames, axis=0)

    def _read(self, name):
        spec = self.profile.get(name)
        return None if spec is None else read_value(self.machine, spec)

    def scores(self):
        return {"agent": self._read("score"), "opponent": self._read("opponent_score")}

    # -------------------------------------------------------------- gym API
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.machine = Chip8(seed=seed)
        self.machine.load_rom(self.rom)
        self.opponent.reset()
        # A few random do-nothing frames so every game doesn't start identically.
        for _ in range(self.np_random.integers(0, 30)):
            self.machine.run_frame()
        self.steps = 0
        self.last = {name: self._read(name) for name in ("score", "opponent_score", "lives", "ball_x")}
        self.ball_direction = 0
        self.hits_this_point = 0
        self.frames.clear()
        screen = self._screen()
        for _ in range(STACK):
            self.frames.append(screen)
        return self._observation(), {}

    def step(self, action):
        p = self.profile
        agent_keys = self.action_keys[int(action)]
        reward = 0.0
        terminated = False

        for _ in range(self.frame_skip):
            self.machine.set_keys(agent_keys | self.opponent.keys(self.machine))
            self.machine.run_frame()
            reward += self._frame_reward()

            if p["end_on_wait_for_key"] and self.machine.waiting_for_key:
                terminated = True
            limit = p["score_limit"]
            if limit is not None and any(s is not None and s >= limit for s in self.scores().values()):
                terminated = True
            if "lives" in p and p["lives"] is not None and self._read("lives") == 0:
                terminated = True
            if terminated:
                break

        self.frames.append(self._screen())
        self.steps += 1
        truncated = not terminated and self.steps >= self.max_steps
        return self._observation(), reward, terminated, truncated, {"scores": self.scores()}

    def _frame_reward(self):
        p = self.profile
        reward = 0.0
        for name, sign in (("score", 1.0), ("opponent_score", -1.0)):
            if name in p and p[name] is not None:
                new = self._read(name)
                d = change(self.last[name], new, p[name])
                if d:
                    reward += sign * d
                    self.hits_this_point = 0      # a point was scored: hit bonuses start again
                self.last[name] = new
        if "lives" in p and p["lives"] is not None:
            new = self._read("lives")
            if change(self.last["lives"], new, p["lives"]) < 0:
                reward -= p["death_penalty"]
            self.last["lives"] = new
        if p["hit_bonus"] and "ball_x" in p:
            reward += self._hit_bonus()
        return reward

    def _hit_bonus(self):
        """Reward the moment the ball turns around on the agent's half of the screen."""
        p = self.profile
        x = self._read("ball_x")
        dx = x - self.last["ball_x"]
        self.last["ball_x"] = x
        if dx == 0 or abs(dx) > 8:              # not moving, or wrapped/reset
            return 0.0
        direction = 1 if dx > 0 else -1
        bonus = 0.0
        agent_on_left = p.get("agent_side", "left") == "left"
        toward_agent = -1 if agent_on_left else 1
        on_agent_half = x < WIDTH // 2 if agent_on_left else x >= WIDTH // 2
        if self.ball_direction == toward_agent and direction == -toward_agent and on_agent_half:
            # Only the first few returns of each point earn a bonus, so the agent can't
            # farm bonuses in an endless rally instead of trying to win the point.
            if self.hits_this_point < p.get("hit_bonus_limit", 3):
                bonus = p["hit_bonus"]
            self.hits_this_point += 1
        self.ball_direction = direction
        return bonus

    def render(self):
        screen = self._screen()
        return np.repeat(screen[:, :, None], 3, axis=2)
