"""Tests for the web API, using a temporary storage folder."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import main, storage

ROMS = Path(__file__).parent / "roms"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE", tmp_path)
    monkeypatch.setattr(storage, "ROM_FOLDER", tmp_path / "roms")
    monkeypatch.setattr(storage, "DATABASE", tmp_path / "test.db")
    return TestClient(main.app)


def upload(client, name):
    with open(ROMS / name, "rb") as f:
        return client.post("/api/roms", files={"file": (name, f.read())})


def test_upload_and_list(client):
    response = upload(client, "2-ibm-logo.ch8")
    assert response.status_code == 200
    rom = response.json()
    assert rom["name"] == "2-ibm-logo" and rom["size"] == 132
    assert client.get("/api/roms").json() == [rom]


def test_same_rom_is_stored_once(client):
    first = upload(client, "skip_test.ch8").json()
    second = upload(client, "skip_test.ch8").json()
    assert first["id"] == second["id"]
    assert len(client.get("/api/roms").json()) == 1


def test_rejects_oversized_rom(client):
    response = client.post("/api/roms", files={"file": ("big.ch8", bytes(4000))})
    assert response.status_code == 400


def test_delete(client):
    rom = upload(client, "f_test.ch8").json()
    assert client.delete(f"/api/roms/{rom['id']}").status_code == 200
    assert client.get("/api/roms").json() == []


def test_play_streams_frames_and_takes_keys(client):
    rom = upload(client, "key_test.ch8").json()
    with client.websocket_connect(f"/ws/play/{rom['id']}") as ws:
        first = ws.receive_bytes()
        assert len(first) == 1 + 64 * 32 and sum(first[1:]) == 0     # blank screen
        ws.send_text('{"type": "key", "key": 7, "down": true}')
        ws.send_text('{"type": "key", "key": 7, "down": false}')
        frame = ws.receive_bytes()
        assert sum(frame[1:]) > 0                                     # the digit 7 appeared
