"""
Watch a trained agent play, in a desktop window.
(The web app's Test tab will do this in the browser later.)

Example (from the backend folder):
    python watch_agent.py storage\\agents\\pong-20261122-190000
"""

import json
import sys
import time
import tkinter as tk
from pathlib import Path

from stable_baselines3 import PPO

from chip8 import HEIGHT, WIDTH
from rl.env import Chip8Env

HERE = Path(__file__).resolve().parent
SCALE = 12


def main():
    if len(sys.argv) < 2:
        print("Usage: python watch_agent.py storage\\agents\\<agent folder>")
        return
    folder = Path(sys.argv[1])
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    profile = summary["profile"]
    rom = (HERE / "storage" / "roms" / f"{summary['rom_id']}.ch8").read_bytes()
    model = PPO.load(folder / "model.zip", device="cpu")
    env = Chip8Env(rom, profile)

    window = tk.Tk()
    window.title(f"Agent: {summary['name']}")
    window.resizable(False, False)
    canvas = tk.Canvas(window, width=WIDTH * SCALE, height=HEIGHT * SCALE, bg="black", highlightthickness=0)
    canvas.pack()
    label = tk.Label(window, font=("Segoe UI", 12))
    label.pack(pady=4)
    boxes = [canvas.create_rectangle((i % WIDTH) * SCALE, (i // WIDTH) * SCALE,
                                     (i % WIDTH + 1) * SCALE, (i // WIDTH + 1) * SCALE,
                                     fill="black", outline="") for i in range(WIDTH * HEIGHT)]
    shown = bytearray(WIDTH * HEIGHT)
    state = {"obs": env.reset()[0], "game": 1}
    step_time = env.frame_skip / 60          # one agent step = frame_skip frames of real time

    def tick():
        started = time.perf_counter()
        action, _ = model.predict(state["obs"], deterministic=True)
        state["obs"], _, terminated, truncated, info = env.step(action)
        for i, pixel in enumerate(env.machine.screen):
            if pixel != shown[i]:
                canvas.itemconfig(boxes[i], fill="white" if pixel else "black")
                shown[i] = pixel
        s = info["scores"]
        label.config(text=f"Game {state['game']}   agent {s['agent']} : {s['opponent']} opponent")
        if terminated or truncated:
            state["obs"], _ = env.reset()
            state["game"] += 1
        delay = max(1, int((step_time - (time.perf_counter() - started)) * 1000))
        window.after(delay, tick)

    tick()
    window.mainloop()


if __name__ == "__main__":
    main()
