"""
Test a saved agent without training it, and record the result.

Plays 50 games two ways (best move, and sampled like in training), prints the result,
saves it to evaluate_log.txt, and stores it in the agent's summary.json.

Example (from the backend folder):
    python evaluate.py storage\\agents\\pong-20261122-191622
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from stable_baselines3 import PPO

from train import evaluate

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Test a saved CHIP-8 agent.")
    parser.add_argument("agent", help="the agent's folder, e.g. storage\\agents\\pong-20261122-191622")
    parser.add_argument("--games", type=int, default=50)
    args = parser.parse_args()

    folder = Path(args.agent)
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    rom = (HERE / "storage" / "roms" / f"{summary['rom_id']}.ch8").read_bytes()
    model = PPO.load(folder / "model.zip", device="cpu")

    print(f"Testing {summary['name']} ({model.num_timesteps:,} steps) on {args.games} games each way...")
    results = evaluate(model, rom, summary["profile"], games=args.games)

    summary["evaluation"] = results
    summary["evaluated_at"] = datetime.now().isoformat(timespec="seconds")
    summary["total_steps"] = model.num_timesteps
    (folder / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = (f"Evaluation of {summary['name']} at {model.num_timesteps:,} steps - "
              f"{datetime.now():%Y-%m-%d %H:%M:%S}\n"
              f"  Best-move play: {results['best_move']}\n"
              f"  Sampled play:   {results['sampled']}\n")
    print(report)
    (HERE / "evaluate_log.txt").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
