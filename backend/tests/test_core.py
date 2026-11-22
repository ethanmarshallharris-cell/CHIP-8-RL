"""
Automated tests for the CHIP-8 core.

Run from the backend folder with:   python -m pytest
"""

from pathlib import Path

import pytest

from chip8 import Chip8, Chip8Error

ROMS = Path(__file__).parent / "roms"


def run_rom(name, frames=200, **kwargs):
    machine = Chip8(seed=1, **kwargs)
    machine.load_rom_file(ROMS / name)
    for _ in range(frames):
        machine.run_frame()
    return machine


# --- the test ROMs from the original build: each passing check moves V3 right by one "8" ---

def test_ibm_logo_draws():
    machine = run_rom("2-ibm-logo.ch8", frames=5)
    assert sum(machine.screen) == 230          # number of lit pixels in the finished logo


def test_skips_and_subroutines():
    machine = run_rom("skip_test.ch8")
    assert machine.V[3] == 6 * 6               # six passes, 6 pixels apart


def test_math_and_flags():
    machine = run_rom("math_test.ch8")
    assert machine.V[3] == 11 * 5              # eleven passes, 5 pixels apart


def test_memory_instructions():
    machine = run_rom("f_test.ch8")
    assert machine.V[3] == 6 * 5               # six passes


def test_timers_count_once_per_frame():
    machine = run_rom("timer_test.ch8", frames=10)
    assert machine.V[3] == 4 * 5               # first four checks pass straight away
    for _ in range(3 * 60):                    # three more delay-timer waits of 60 frames
        machine.run_frame()
    assert machine.V[3] == 7 * 5


def test_sound_timer_beeps():
    machine = run_rom("beep_test.ch8", frames=2)
    assert machine.beeping


# --- keyboard ---

def test_wait_for_key_needs_a_release():
    machine = run_rom("key_test.ch8", frames=5)
    assert machine.waiting_for_key
    machine.key_down(0x7)
    machine.run_frame()
    assert machine.waiting_for_key            # pressed but not yet released: still waiting
    machine.key_up(0x7)
    machine.run_frame()
    assert machine.V[0] == 0x7                # the released key was stored
    assert sum(machine.screen) > 0            # and its digit was drawn


def test_set_keys_reports_releases():
    machine = run_rom("key_test.ch8", frames=5)
    machine.set_keys({0xA})
    machine.run_frame()
    machine.set_keys(set())                   # letting go of A counts as a release
    machine.run_frame()
    assert machine.V[0] == 0xA


# --- hooks used later by the reward tools ---

def test_displayed_numbers_hook():
    machine = Chip8()
    # V0 = 156; I = 0x300; FX33 (BCD of V0); loop
    machine.load_rom(bytes.fromhex("609C A300 F033 1206"))
    for _ in range(2):
        machine.run_frame()
    assert machine.displayed_numbers == {0x204: (0, 156)}
    assert machine.memory[0x300:0x303] == bytes([1, 5, 6])


def test_save_and_restore_state():
    machine = run_rom("timer_test.ch8", frames=20)
    saved = machine.get_state()
    for _ in range(100):
        machine.run_frame()
    after_100 = machine.get_state()

    machine.set_state(saved)                  # go back in time...
    for _ in range(100):
        machine.run_frame()
    assert machine.get_state() == after_100   # ...and the same 100 frames happen again


def test_reset_restarts_the_rom():
    machine = run_rom("skip_test.ch8")
    machine.reset()
    assert machine.pc == 0x200 and machine.V[3] == 0 and sum(machine.screen) == 0


# --- errors ---

def test_rejects_oversized_rom():
    with pytest.raises(Chip8Error):
        Chip8().load_rom(bytes(4000))


def test_rejects_empty_rom():
    with pytest.raises(Chip8Error):
        Chip8().load_rom(b"")


def test_return_with_empty_stack_is_an_error():
    machine = Chip8()
    machine.load_rom(bytes.fromhex("00EE"))
    with pytest.raises(Chip8Error):
        machine.step()


def test_unknown_opcodes_are_recorded():
    machine = Chip8()
    machine.load_rom(bytes.fromhex("E0FF 1202"))
    machine.step()
    assert 0xE0FF in machine.unknown_opcodes
