"""
A simple desktop player for the CHIP-8 core, using tkinter.
(The web app's Play tab will replace this; it's kept for quick local testing.)

Run from the backend folder:   python play_desktop.py "path\\to\\game.ch8"
"""

import sys
import tempfile
import time
import tkinter as tk
import wave
from pathlib import Path
from tkinter import filedialog

from chip8 import Chip8, WIDTH, HEIGHT

SCALE = 12
FRAME_TIME = 1 / 60          # one CHIP-8 frame (one timer tick) = 1/60 s

KEY_MAP = {
    "1": 0x1, "2": 0x2, "3": 0x3, "4": 0xC,
    "q": 0x4, "w": 0x5, "e": 0x6, "r": 0xD,
    "a": 0x7, "s": 0x8, "d": 0x9, "f": 0xE,
    "z": 0xA, "x": 0x0, "c": 0xB, "v": 0xF,
}

try:
    import winsound           # Windows only - the player still works without sound elsewhere
except ImportError:
    winsound = None

BEEP_FILE = Path(tempfile.gettempdir()) / "chip8_beep.wav"


def make_beep_file(pitch=441, volume=30, sample_rate=44100):
    """Write a short square-wave tone that can be looped while the sound timer runs."""
    half = sample_rate // pitch // 2
    samples = bytes(([128 + volume] * half + [128 - volume] * half) * 44)
    with wave.open(str(BEEP_FILE), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(sample_rate)
        wav.writeframes(samples)


def set_beep(on):
    if winsound is None:
        return
    if on:
        winsound.PlaySound(str(BEEP_FILE), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
    else:
        winsound.PlaySound(None, 0)


def main():
    window = tk.Tk()
    window.title("CHIP-8")
    window.resizable(False, False)

    rom_path = sys.argv[1] if len(sys.argv) > 1 else filedialog.askopenfilename(
        title="Choose a CHIP-8 ROM", filetypes=[("CHIP-8 ROMs", "*.ch8"), ("All files", "*.*")])
    if not rom_path:
        return

    machine = Chip8()
    machine.load_rom_file(rom_path)

    canvas = tk.Canvas(window, width=WIDTH * SCALE, height=HEIGHT * SCALE,
                       bg="black", highlightthickness=0)
    canvas.pack()
    boxes = [canvas.create_rectangle((i % WIDTH) * SCALE, (i // WIDTH) * SCALE,
                                     (i % WIDTH + 1) * SCALE, (i // WIDTH + 1) * SCALE,
                                     fill="black", outline="")
             for i in range(WIDTH * HEIGHT)]
    shown = bytearray(WIDTH * HEIGHT)

    def on_key(event, pressed):
        key = KEY_MAP.get(event.keysym.lower())
        if key is not None:
            machine.key_down(key) if pressed else machine.key_up(key)

    window.bind("<KeyPress>", lambda e: on_key(e, True))
    window.bind("<KeyRelease>", lambda e: on_key(e, False))

    state = {"last": time.perf_counter(), "owed": 0.0, "beeping": False}

    def tick():
        now = time.perf_counter()
        state["owed"] += now - state["last"]
        state["last"] = now
        frames = 0
        while state["owed"] >= FRAME_TIME and frames < 5:   # catch up, but never spiral
            machine.run_frame()
            state["owed"] -= FRAME_TIME
            frames += 1
        if frames == 5:
            state["owed"] = 0.0

        for i, pixel in enumerate(machine.screen):
            if pixel != shown[i]:
                canvas.itemconfig(boxes[i], fill="white" if pixel else "black")
                shown[i] = pixel

        if machine.beeping != state["beeping"]:
            set_beep(machine.beeping)
            state["beeping"] = machine.beeping

        window.after(5, tick)

    def close():
        set_beep(False)
        window.destroy()

    if winsound:
        make_beep_file()
    window.protocol("WM_DELETE_WINDOW", close)
    window.focus_force()
    tick()
    window.mainloop()


if __name__ == "__main__":
    main()
