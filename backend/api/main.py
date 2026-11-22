"""
The web server: REST routes for ROMs, and a WebSocket that streams a live game.

Start it from the backend folder with:   python serve.py
"""

import asyncio
import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from chip8 import Chip8, Chip8Error
from chip8.core import MAX_ROM_SIZE

from . import storage

app = FastAPI(title="CHIP-8 RL")

FRAME_TIME = 1 / 60


# ---------------------------------------------------------------- ROMs (REST)

@app.get("/api/roms")
def list_roms():
    return storage.list_roms()


@app.post("/api/roms")
async def upload_rom(file: UploadFile):
    data = await file.read()
    if not data:
        raise HTTPException(400, "The file is empty.")
    if len(data) > MAX_ROM_SIZE:
        raise HTTPException(400, f"That file is {len(data):,} bytes; CHIP-8 ROMs are at most {MAX_ROM_SIZE:,}.")
    name = Path(file.filename or "rom").stem
    return storage.add_rom(name, data)


@app.delete("/api/roms/{rom_id}")
def delete_rom(rom_id: str):
    record, _ = storage.get_rom(rom_id)
    if record is None:
        raise HTTPException(404, "No such ROM.")
    storage.delete_rom(rom_id)
    return {"deleted": rom_id}


# ---------------------------------------------------------------- live play (WebSocket)
#
# Server -> browser: binary messages, one per frame that changed:
#     byte 0      = flags (bit 0: beeping)
#     bytes 1..   = the 2,048 screen pixels (0 or 1), row by row
# Browser -> server: JSON text messages:
#     {"type": "key", "key": 5, "down": true}
#     {"type": "reset"}
#     {"type": "pause", "paused": true}

@app.websocket("/ws/play/{rom_id}")
async def play(websocket: WebSocket, rom_id: str):
    await websocket.accept()
    record, data = storage.get_rom(rom_id)
    if record is None:
        await websocket.close(code=4404, reason="No such ROM.")
        return

    machine = Chip8()
    machine.load_rom(data)
    session = {"paused": False}

    async def receive_input():
        while True:
            message = json.loads(await websocket.receive_text())
            if message["type"] == "key":
                key = int(message["key"]) & 0xF
                machine.key_down(key) if message["down"] else machine.key_up(key)
            elif message["type"] == "reset":
                machine.reset()
            elif message["type"] == "pause":
                session["paused"] = bool(message["paused"])

    async def run_game():
        last_sent = None
        next_frame = time.perf_counter()
        while True:
            if not session["paused"]:
                machine.run_frame()
            frame = bytes([1 if machine.beeping else 0]) + bytes(machine.screen)
            if frame != last_sent:                   # only send frames that changed
                await websocket.send_bytes(frame)
                last_sent = frame

            next_frame += FRAME_TIME                 # keep a steady 60 frames per second
            delay = next_frame - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
            else:
                next_frame = time.perf_counter()     # fell behind - don't try to catch up

    tasks = [asyncio.create_task(receive_input()), asyncio.create_task(run_game())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            error = task.exception()
            if isinstance(error, Chip8Error):
                await websocket.close(code=4500, reason=str(error)[:120])
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            task.cancel()


# ---------------------------------------------------------------- the built React app
# After "npm run build", the finished web app in frontend/dist is served from here,
# so the whole thing runs from one address: http://localhost:8000

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        return FileResponse(FRONTEND / "index.html")
