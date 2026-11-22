import { useEffect, useRef, useState } from "react";
import { openPlaySocket } from "../api.js";
import Chip8Screen from "../components/Chip8Screen.jsx";
import RomLibrary from "../components/RomLibrary.jsx";

// Laptop key -> CHIP-8 key (the standard 1234 / QWER / ASDF / ZXCV layout)
const KEY_MAP = {
  1: 0x1, 2: 0x2, 3: 0x3, 4: 0xc,
  q: 0x4, w: 0x5, e: 0x6, r: 0xd,
  a: 0x7, s: 0x8, d: 0x9, f: 0xe,
  z: 0xa, x: 0x0, c: 0xb, v: 0xf,
};

// A small square-wave beep using the browser's Web Audio API.
function createBeeper() {
  const audio = new AudioContext();
  audio.resume(); // browsers start audio paused until the page has been clicked
  const gain = audio.createGain();
  gain.gain.value = 0;
  gain.connect(audio.destination);
  const tone = audio.createOscillator();
  tone.type = "square";
  tone.frequency.value = 441;
  tone.connect(gain);
  tone.start();
  return {
    set(on) {
      gain.gain.setTargetAtTime(on ? 0.05 : 0, audio.currentTime, 0.005);
    },
    close() {
      audio.close();
    },
  };
}

export default function PlayTab() {
  const [rom, setRom] = useState(null);
  const [status, setStatus] = useState("Choose a ROM to play.");
  const [paused, setPaused] = useState(false);
  const screenRef = useRef(null);
  const socketRef = useRef(null);

  // Whenever a different ROM is chosen, open a new live game for it.
  useEffect(() => {
    if (!rom) {
      screenRef.current?.clear();
      return;
    }
    const socket = openPlaySocket(rom.id);
    const beeper = createBeeper();
    socketRef.current = socket;
    setPaused(false);
    setStatus(`Connecting to ${rom.name}…`);

    socket.onopen = () => setStatus(`Playing ${rom.name}`);
    socket.onmessage = (event) => {
      const frame = new Uint8Array(event.data);
      beeper.set(frame[0] & 1);
      screenRef.current.draw(frame.subarray(1));
    };
    socket.onclose = (event) => {
      beeper.set(false);
      if (event.code >= 4000) setStatus(`Stopped: ${event.reason}`);
    };

    const send = (message) => {
      if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
    };
    const onKey = (down) => (event) => {
      const key = KEY_MAP[event.key.toLowerCase()];
      if (key === undefined || event.repeat) return;
      event.preventDefault();
      send({ type: "key", key, down });
    };
    const keyDown = onKey(true);
    const keyUp = onKey(false);
    window.addEventListener("keydown", keyDown);
    window.addEventListener("keyup", keyUp);

    // Clean up when the ROM changes or the tab is closed.
    return () => {
      window.removeEventListener("keydown", keyDown);
      window.removeEventListener("keyup", keyUp);
      socket.close();
      beeper.close();
    };
  }, [rom]);

  function send(message) {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
  }

  function togglePause() {
    send({ type: "pause", paused: !paused });
    setPaused(!paused);
  }

  return (
    <div className="split">
      <RomLibrary selectedId={rom?.id} onSelect={setRom} />
      <section className="player">
        <Chip8Screen ref={screenRef} />
        <div className="controls">
          <span className="status">{status}</span>
          <button disabled={!rom} onClick={togglePause}>
            {paused ? "Resume" : "Pause"}
          </button>
          <button disabled={!rom} onClick={() => send({ type: "reset" })}>
            Reset
          </button>
        </div>
        <p className="muted">Keys: 1 2 3 4 / Q W E R / A S D F / Z X C V</p>
      </section>
    </div>
  );
}
