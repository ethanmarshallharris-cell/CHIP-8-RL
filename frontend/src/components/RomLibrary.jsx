import { useEffect, useRef, useState } from "react";
import { deleteRom, listRoms, uploadRom } from "../api.js";

// Lists the stored ROMs, lets the user upload new ones, and reports which one is selected.
export default function RomLibrary({ selectedId, onSelect }) {
  const [roms, setRoms] = useState([]);
  const [error, setError] = useState("");
  const fileInput = useRef(null);

  async function refresh() {
    try {
      setRoms(await listRoms());
      setError("");
    } catch (e) {
      setError(`Couldn't reach the backend: ${e.message}. Is "python serve.py" running?`);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleUpload(event) {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    try {
      const rom = await uploadRom(file);
      await refresh();
      onSelect(rom);
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleDelete(rom) {
    if (!window.confirm(`Remove "${rom.name}" from the library?`)) return;
    await deleteRom(rom.id);
    if (rom.id === selectedId) onSelect(null);
    refresh();
  }

  return (
    <aside className="library">
      <div className="library-header">
        <h2>ROMs</h2>
        <button onClick={() => fileInput.current.click()}>Upload ROM</button>
        <input ref={fileInput} type="file" accept=".ch8,.c8,.rom" hidden onChange={handleUpload} />
      </div>
      {error && <p className="error">{error}</p>}
      {roms.length === 0 && !error && <p className="muted">No ROMs yet. Upload a .ch8 file to start.</p>}
      <ul>
        {roms.map((rom) => (
          <li key={rom.id} className={rom.id === selectedId ? "selected" : ""}>
            <button className="rom-name" onClick={() => onSelect(rom)}>
              {rom.name}
            </button>
            <button className="icon" title="Remove" onClick={() => handleDelete(rom)}>
              ✕
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
