"""
The CHIP-8 machine itself - no window, no sound, no keyboard handling.

Anything that wants to run CHIP-8 (the web app, a desktop player, an RL agent)
creates a Chip8 object, loads a ROM, and calls run_frame() repeatedly.
"""

import random

MEMORY_SIZE = 4096
FONT_START = 0x050
PROGRAM_START = 0x200
MAX_ROM_SIZE = MEMORY_SIZE - PROGRAM_START
WIDTH = 64
HEIGHT = 32

FONTSET = bytes([
    0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
    0x20, 0x60, 0x20, 0x20, 0x70,  # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
    0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
    0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
    0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
    0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
    0xF0, 0x80, 0xF0, 0x80, 0x80,  # F
])

MAX_STACK_DEPTH = 16


class Chip8Error(Exception):
    """Raised when a ROM can't be loaded or the program does something impossible."""


class Chip8:
    def __init__(self, instructions_per_frame=10, seed=None):
        self.instructions_per_frame = instructions_per_frame
        self.random = random.Random(seed)     # own random generator, so runs can be repeated
        self.rom = b""
        self.reset()

    # ------------------------------------------------------------------ setup
    def reset(self):
        """Put the machine back to its power-on state, keeping the loaded ROM."""
        self.memory = bytearray(MEMORY_SIZE)
        self.memory[FONT_START:FONT_START + len(FONTSET)] = FONTSET
        self.memory[PROGRAM_START:PROGRAM_START + len(self.rom)] = self.rom

        self.V = [0] * 16
        self.I = 0
        self.pc = PROGRAM_START
        self.stack = []
        self.delay_timer = 0
        self.sound_timer = 0

        self.screen = bytearray(WIDTH * HEIGHT)   # pixel (x, y) is screen[y * WIDTH + x]
        self.keys = [False] * 16
        self.released_key = None

        self.waiting_for_key = False      # True while the program is stuck on FX0A
        self.displayed_numbers = {}       # FX33 hook: {pc address: (register, last value)}
        self.unknown_opcodes = set()      # opcodes this program used that we don't support
        self.frame_count = 0

    def load_rom(self, rom_bytes):
        """Load a ROM (given as bytes) and reset the machine."""
        rom_bytes = bytes(rom_bytes)
        if len(rom_bytes) == 0:
            raise Chip8Error("The ROM is empty.")
        if len(rom_bytes) > MAX_ROM_SIZE:
            raise Chip8Error(f"The ROM is {len(rom_bytes):,} bytes; the limit is {MAX_ROM_SIZE:,}.")
        self.rom = rom_bytes
        self.reset()

    def load_rom_file(self, path):
        """Load a ROM from a file path."""
        with open(path, "rb") as f:
            self.load_rom(f.read())

    # ------------------------------------------------------------------ input
    def key_down(self, key):
        self.keys[key & 0xF] = True

    def key_up(self, key):
        self.keys[key & 0xF] = False
        self.released_key = key & 0xF

    def set_keys(self, pressed):
        """Set the whole keypad at once from a collection of held keys (used by RL agents)."""
        for k in range(16):
            held = k in pressed
            if self.keys[k] and not held:
                self.released_key = k
            self.keys[k] = held

    # ------------------------------------------------------------------ running
    def run_frame(self):
        """Run one frame: a batch of instructions, then one timer tick (1/60 s of CHIP-8 time)."""
        for _ in range(self.instructions_per_frame):
            self.step()
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1
        self.released_key = None
        self.frame_count += 1

    def step(self):
        """Fetch, decode and execute one instruction."""
        opcode = (self.memory[self.pc] << 8) | self.memory[(self.pc + 1) & 0xFFF]
        self.pc = (self.pc + 2) & 0xFFF
        self.execute(opcode)

    def execute(self, opcode):
        V = self.V
        kind = (opcode & 0xF000) >> 12
        x    = (opcode & 0x0F00) >> 8
        y    = (opcode & 0x00F0) >> 4
        n    =  opcode & 0x000F
        nn   =  opcode & 0x00FF
        nnn  =  opcode & 0x0FFF

        if opcode == 0x00E0:
            for i in range(len(self.screen)):
                self.screen[i] = 0
        elif opcode == 0x00EE:
            if not self.stack:
                raise Chip8Error(f"Return with an empty stack at {self.pc - 2:03X}.")
            self.pc = self.stack.pop()
        elif kind == 0x1:
            self.pc = nnn
        elif kind == 0x2:
            if len(self.stack) >= MAX_STACK_DEPTH:
                raise Chip8Error(f"Stack overflow (more than {MAX_STACK_DEPTH} calls) at {self.pc - 2:03X}.")
            self.stack.append(self.pc)
            self.pc = nnn
        elif kind == 0x3:
            if V[x] == nn:
                self.pc += 2
        elif kind == 0x4:
            if V[x] != nn:
                self.pc += 2
        elif kind == 0x5:
            if V[x] == V[y]:
                self.pc += 2
        elif kind == 0x6:
            V[x] = nn
        elif kind == 0x7:
            V[x] = (V[x] + nn) & 0xFF
        elif kind == 0x8:
            self._math(x, y, n)
        elif kind == 0x9:
            if V[x] != V[y]:
                self.pc += 2
        elif kind == 0xA:
            self.I = nnn
        elif kind == 0xB:
            self.pc = (nnn + V[0]) & 0xFFF
        elif kind == 0xC:
            V[x] = self.random.randint(0, 255) & nn
        elif kind == 0xD:
            self._draw(V[x], V[y], n)
        elif kind == 0xE and nn == 0x9E:
            if self.keys[V[x] & 0xF]:
                self.pc += 2
        elif kind == 0xE and nn == 0xA1:
            if not self.keys[V[x] & 0xF]:
                self.pc += 2
        elif kind == 0xF:
            self._misc(opcode, x, nn)
        else:
            self.unknown_opcodes.add(opcode)

    def _math(self, x, y, n):
        V = self.V
        if n == 0x0:
            V[x] = V[y]
        elif n == 0x1:
            V[x] |= V[y]
        elif n == 0x2:
            V[x] &= V[y]
        elif n == 0x3:
            V[x] ^= V[y]
        elif n == 0x4:
            total = V[x] + V[y]
            V[x] = total & 0xFF
            V[0xF] = 1 if total > 0xFF else 0
        elif n == 0x5:
            flag = 1 if V[x] >= V[y] else 0
            V[x] = (V[x] - V[y]) & 0xFF
            V[0xF] = flag
        elif n == 0x6:
            flag = V[x] & 1
            V[x] >>= 1
            V[0xF] = flag
        elif n == 0x7:
            flag = 1 if V[y] >= V[x] else 0
            V[x] = (V[y] - V[x]) & 0xFF
            V[0xF] = flag
        elif n == 0xE:
            flag = (V[x] >> 7) & 1
            V[x] = (V[x] << 1) & 0xFF
            V[0xF] = flag
        else:
            self.unknown_opcodes.add(0x8000 | (x << 8) | (y << 4) | n)

    def _draw(self, vx, vy, height):
        start_x = vx % WIDTH
        start_y = vy % HEIGHT
        screen = self.screen
        collision = 0
        for row in range(height):
            py = start_y + row
            if py >= HEIGHT:
                break
            sprite_byte = self.memory[(self.I + row) & 0xFFF]
            for col in range(8):
                px = start_x + col
                if px >= WIDTH:
                    break
                if (sprite_byte >> (7 - col)) & 1:
                    i = py * WIDTH + px
                    if screen[i]:
                        collision = 1
                    screen[i] ^= 1
        self.V[0xF] = collision

    def _misc(self, opcode, x, nn):
        V = self.V
        mem = self.memory
        if nn == 0x07:
            V[x] = self.delay_timer
        elif nn == 0x0A:
            if self.released_key is None:
                self.waiting_for_key = True
                self.pc -= 2
            else:
                self.waiting_for_key = False
                V[x] = self.released_key
                self.released_key = None
        elif nn == 0x15:
            self.delay_timer = V[x]
        elif nn == 0x18:
            self.sound_timer = V[x]
        elif nn == 0x1E:
            self.I = (self.I + V[x]) & 0xFFF
        elif nn == 0x29:
            self.I = FONT_START + (V[x] & 0xF) * 5
        elif nn == 0x33:
            value = V[x]
            mem[self.I & 0xFFF] = value // 100
            mem[(self.I + 1) & 0xFFF] = (value // 10) % 10
            mem[(self.I + 2) & 0xFFF] = value % 10
            self.displayed_numbers[self.pc - 2] = (x, value)    # hook for the score finder
        elif nn == 0x55:
            for r in range(x + 1):
                mem[(self.I + r) & 0xFFF] = V[r]
        elif nn == 0x65:
            for r in range(x + 1):
                V[r] = mem[(self.I + r) & 0xFFF]
        else:
            self.unknown_opcodes.add(opcode)

    # ------------------------------------------------------------------ inspection
    @property
    def beeping(self):
        """True while the sound timer says a tone should play."""
        return self.sound_timer > 0

    def pixel(self, x, y):
        return self.screen[y * WIDTH + x]

    def screen_text(self, on="#", off="."):
        """The screen as text, one line per row (handy for tests and debugging)."""
        rows = []
        for y in range(HEIGHT):
            rows.append("".join(on if self.screen[y * WIDTH + x] else off for x in range(WIDTH)))
        return "\n".join(rows)

    # ------------------------------------------------------------------ save / restore
    def get_state(self):
        """A snapshot of everything needed to resume the machine exactly where it was."""
        return {
            "memory": bytes(self.memory),
            "V": list(self.V),
            "I": self.I,
            "pc": self.pc,
            "stack": list(self.stack),
            "delay_timer": self.delay_timer,
            "sound_timer": self.sound_timer,
            "screen": bytes(self.screen),
            "keys": list(self.keys),
            "waiting_for_key": self.waiting_for_key,
            "frame_count": self.frame_count,
            "random_state": self.random.getstate(),
        }

    def set_state(self, state):
        """Restore a snapshot made by get_state()."""
        self.memory = bytearray(state["memory"])
        self.V = list(state["V"])
        self.I = state["I"]
        self.pc = state["pc"]
        self.stack = list(state["stack"])
        self.delay_timer = state["delay_timer"]
        self.sound_timer = state["sound_timer"]
        self.screen = bytearray(state["screen"])
        self.keys = list(state["keys"])
        self.released_key = None
        self.waiting_for_key = state["waiting_for_key"]
        self.frame_count = state["frame_count"]
        self.random.setstate(state["random_state"])
