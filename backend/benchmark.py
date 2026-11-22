"""
Measure how fast the CHIP-8 core runs, and save the result to benchmark_log.txt.

Run from the backend folder:   python benchmark.py
"""

import time
from datetime import datetime
from pathlib import Path

from chip8 import Chip8

HERE = Path(__file__).resolve().parent
ROMS = [HERE / "tests" / "roms" / "math_test.ch8", HERE / "tests" / "roms" / "2-ibm-logo.ch8"]
SECONDS = 3


def measure(rom_path):
    machine = Chip8()
    machine.load_rom_file(rom_path)
    frames = 0
    start = time.perf_counter()
    while time.perf_counter() - start < SECONDS:
        for _ in range(100):
            machine.run_frame()
            frames += 1
    elapsed = time.perf_counter() - start
    return frames / elapsed


def main():
    lines = [f"CHIP-8 core benchmark - {datetime.now():%Y-%m-%d %H:%M:%S}", ""]
    for rom in ROMS:
        fps = measure(rom)
        ips = fps * Chip8().instructions_per_frame
        lines.append(f"{rom.name:<18} {fps:>10,.0f} frames/s   {ips:>12,.0f} instructions/s"
                     f"   ({fps / 60:,.0f}x real time)")
    report = "\n".join(lines)
    print(report)
    (HERE / "benchmark_log.txt").write_text(report + "\n", encoding="utf-8")
    print(f"\nSaved to {HERE / 'benchmark_log.txt'}")


if __name__ == "__main__":
    main()
