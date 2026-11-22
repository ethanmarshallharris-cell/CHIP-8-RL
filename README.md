# CHIP-8 RL

A CHIP-8 emulator written in Python, being extended into a web app for training
reinforcement-learning agents to play CHIP-8 games — on an ordinary laptop, no GPU required.

## Status

🚧 In progress.

- [x] Emulator core (`backend/chip8`) with automated tests
- [x] Web backend (FastAPI) and Play tab (React)
- [x] Reinforcement-learning environment, reward profiles and score finder (command line)
- [ ] Train and Test tabs (React)

## Project layout

```
backend/
  chip8/           the CHIP-8 machine (no window, no sound - just the emulator)
  tests/           automated tests and test ROMs
  play_desktop.py  quick desktop player using tkinter
  benchmark.py     measures how fast the core runs
  run_tests.py     runs the tests and saves a log
  api/             FastAPI web server: ROM library (REST) and live play (WebSocket)
  serve.py         starts the web server
  rl/              Gymnasium environment, reward profiles, score finder, opponents
  find_score.py    finds where a game keeps its score
  train.py         trains an agent (PPO) from the command line
  watch_agent.py   watches a trained agent play
frontend/          React web app (Vite)
```

## How it works

The Python backend runs the emulator. The React frontend shows it in the browser:
the backend streams each changed frame over a WebSocket (64 x 32 pixels plus a beep flag),
and the browser sends key presses back. ROMs are stored once each, identified by a hash
of their contents, in a SQLite database.

## Reinforcement learning

Each game gets a small **reward profile** (`backend/rl/profiles/`) saying which keys it
uses, where its score lives, and how a game ends. CHIP-8 has no standard place for a
score, so `find_score.py` plays the game with random inputs and reports numbers that
behave like a score - starting with numbers the game displays using the `FX33`
instruction, then falling back to a search of every register and memory byte.

Two-player games such as Pong get a rule-based opponent that tracks the ball, so the
agent always plays one side against a consistent opponent. Rewards are +1 for the
agent's points and -1 for the opponent's, plus a small bonus for returning the ball
(limited per point so it can't be farmed).

The agent sees the last four 64 x 32 screens and is trained with PPO
(Stable-Baselines3) using a small convolutional network sized for CHIP-8's screen,
on the CPU, with several games running in parallel.

## Running it

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_tests.py
```

Then, to use the web app (needs [Node.js](https://nodejs.org) LTS), build the frontend once
and start the server:

```
cd frontend
npm install
npm run build
cd ..\backend
python serve.py
```

Open http://localhost:8000. While developing the frontend, run `npm run dev` in `frontend`
as well and use http://localhost:5173 instead - it reloads instantly when you save a file.

`python play_desktop.py` in `backend` opens a quick desktop player without the web app.

To find a game's score and train an agent (from `backend`):

```
python find_score.py storage\roms\<rom id>.ch8 --keys 1 Q 4 R
python train.py --rom storage\roms\<rom id>.ch8 --profile rl\profiles\pong.json --steps 500000
python watch_agent.py storage\agents\<agent folder>
```

Controls use the standard CHIP-8 layout: `1 2 3 4 / Q W E R / A S D F / Z X C V`.

## Credits

- Test ROM `2-ibm-logo.ch8` is from Timendus's
  [CHIP-8 test suite](https://github.com/Timendus/chip8-test-suite) (GPL-3.0).
- The other test ROMs in `backend/tests/roms` were written for this project.
