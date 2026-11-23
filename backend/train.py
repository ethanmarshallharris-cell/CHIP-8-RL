"""
Train an agent from the command line.

Start a new agent (from the backend folder):
    python train.py --rom storage\\roms\\1db31d734b9352f9.ch8 --profile rl\\profiles\\pong.json --steps 1000000

Keep training an existing agent:
    python train.py --continue-from storage\\agents\\pong-20261122-191622 --steps 1000000

Progress is printed and saved to training_log.txt. The agent is saved to
storage\\agents\\<name>\\ (model.zip plus summary.json) every 100,000 steps, when training
finishes, and if you stop early with Ctrl+C - so you can watch it at any point with
watch_agent.py, even while training is still running.
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv

from rl.env import Chip8Env
from rl.networks import Chip8CNN
from rl.profiles import load_profile

HERE = Path(__file__).resolve().parent


class Checkpoints(BaseCallback):
    """Save the agent every so often, so it can be watched mid-training and isn't lost if stopped."""

    def __init__(self, save, every_steps=100_000):
        super().__init__()
        self.save = save
        self.every = every_steps
        self.next_save = every_steps

    def _on_training_start(self):
        # A continued agent's step count doesn't start at 0, so count from where it is now.
        self.next_save = self.num_timesteps + self.every

    def _on_step(self):
        if self.num_timesteps >= self.next_save:
            self.next_save += self.every
            self.save(self.model, status="training")
        return True


class ProgressLog(BaseCallback):
    """Every so often, print and log the average result of recent games."""

    def __init__(self, log_path, every_steps=20_000):
        super().__init__()
        self.log_path = log_path
        self.every = every_steps
        self.next_report = every_steps
        self.returns, self.results = [], []
        self.episode_return = None
        self.start = time.time()

    def _on_training_start(self):
        self.episode_return = np.zeros(self.training_env.num_envs)
        # A continued agent's step count doesn't start at 0, so count from where it is now.
        self.next_report = self.num_timesteps + self.every

    def _on_step(self):
        self.episode_return += self.locals["rewards"]
        for i, done in enumerate(self.locals["dones"]):
            if done:
                scores = self.locals["infos"][i]["scores"]
                self.returns.append(self.episode_return[i])
                self.results.append((scores["agent"] or 0) - (scores["opponent"] or 0))
                self.episode_return[i] = 0
        if self.num_timesteps >= self.next_report:
            self.next_report += self.every
            recent_r, recent_s = self.returns[-50:], self.results[-50:]
            line = (f"{self.num_timesteps:>10,} steps | {time.time() - self.start:>6.0f} s | "
                    f"games {len(self.returns):>5} | avg reward {np.mean(recent_r) if recent_r else 0:>6.2f} | "
                    f"avg score difference {np.mean(recent_s) if recent_s else 0:>5.2f}")
            print(line)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return True


def play_games(model, rom, profile, games, deterministic):
    env = Chip8Env(rom, profile, seed=12345)
    wins = losses = 0
    differences = []
    for game in range(games):
        obs, _ = env.reset(seed=1000 + game)
        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=deterministic)
            obs, _, terminated, truncated, info = env.step(action)
            done = terminated or truncated
        mine, theirs = info["scores"]["agent"] or 0, info["scores"]["opponent"] or 0
        differences.append(mine - theirs)
        wins += mine > theirs
        losses += mine < theirs
    return {"games": games, "wins": wins, "losses": losses, "draws": games - wins - losses,
            "avg_score_difference": round(float(np.mean(differences)), 2)}


def evaluate(model, rom, profile, games=50):
    """
    Test the agent two ways:
      best_move - always the action it rates highest (how agents are usually shown off)
      sampled   - picking actions with the same randomness it used while training
    """
    return {"best_move": play_games(model, rom, profile, games, deterministic=True),
            "sampled": play_games(model, rom, profile, games, deterministic=False)}


def main():
    parser = argparse.ArgumentParser(description="Train a CHIP-8 agent with PPO.")
    parser.add_argument("--rom", help="ROM file (not needed with --continue-from)")
    parser.add_argument("--profile", help="reward profile (not needed with --continue-from)")
    parser.add_argument("--continue-from", help="an agent folder to keep training")
    parser.add_argument("--steps", type=int, default=1_000_000, help="agent steps to train for this run")
    parser.add_argument("--envs", type=int, default=4, help="games running in parallel (one per CPU core)")
    parser.add_argument("--learning-rate", type=float, default=2.5e-4)
    parser.add_argument("--name", default=None, help="name for a new agent")
    args = parser.parse_args()

    previous = None
    if args.continue_from:
        out = Path(args.continue_from)
        previous = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        profile = previous["profile"]
        rom = (HERE / "storage" / "roms" / f"{previous['rom_id']}.ch8").read_bytes()
        name = previous["name"]
    else:
        if not (args.rom and args.profile):
            parser.error("--rom and --profile are needed to start a new agent")
        rom = Path(args.rom).read_bytes()
        profile = load_profile(args.profile)
        name = args.name or f"{Path(args.profile).stem}-{datetime.now():%Y%m%d-%H%M%S}"
        out = HERE / "storage" / "agents" / name
    out.mkdir(parents=True, exist_ok=True)

    log_path = HERE / "training_log.txt"
    action = "Continuing" if previous else "Training"
    log_path.write_text(f"{action} {name} - {datetime.now():%Y-%m-%d %H:%M:%S}\n", encoding="utf-8")

    env = make_vec_env(lambda: Chip8Env(rom, profile), n_envs=args.envs,
                       vec_env_cls=SubprocVecEnv if args.envs > 1 else None, seed=0)
    if previous:
        model = PPO.load(out / "model.zip", env=env, device="cpu")
    else:
        model = PPO(
            "CnnPolicy", env,
            policy_kwargs={"features_extractor_class": Chip8CNN},
            learning_rate=args.learning_rate,
            n_steps=256, batch_size=256, n_epochs=4,
            gamma=0.99, gae_lambda=0.95, clip_range=0.1, ent_coef=0.01,
            device="cpu", verbose=0, seed=0,
        )

    started = time.time()
    earlier_seconds = previous["training_seconds"] if previous else 0

    def save(model, status, evaluation=None):
        """Write model.zip and summary.json (written to temporary names first, so a
        watcher never reads a half-written file)."""
        model.save(out / "model-saving.zip")
        (out / "model-saving.zip").replace(out / "model.zip")
        summary = {
            "name": name, "rom_id": profile.get("rom_id"), "profile": profile,
            "algorithm": "PPO", "status": status,
            "total_steps": model.num_timesteps,      # keeps counting across continued runs
            "envs": args.envs, "learning_rate": args.learning_rate,
            "training_seconds": earlier_seconds + round(time.time() - started),
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "evaluation": evaluation if evaluation is not None else (previous or {}).get("evaluation"),
        }
        temp = out / "summary-saving.json"
        temp.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        temp.replace(out / "summary.json")
        return summary

    stopped_early = False
    try:
        model.learn(total_timesteps=args.steps, reset_num_timesteps=not previous,
                    callback=[ProgressLog(log_path), Checkpoints(save)])
    except KeyboardInterrupt:
        stopped_early = True
        print("\nStopped early - saving the agent as it is now...")
    try:
        env.close()
    except (EOFError, BrokenPipeError, ConnectionResetError):
        pass        # after Ctrl+C the background game processes may already have exited

    print("Testing the agent on 50 games each way (this takes a minute)...")
    results = evaluate(model, rom, profile)
    summary = save(model, "stopped early" if stopped_early else "finished", results)
    line = (f"\n{summary['status'].capitalize()} after {summary['total_steps']:,} total steps "
            f"({summary['training_seconds']} s).\n"
            f"  Best-move play: {results['best_move']}\n"
            f"  Sampled play:   {results['sampled']}\n"
            f"Saved to {out}")
    print(line)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


if __name__ == "__main__":       # required on Windows when games run in parallel processes
    main()
