// Small helpers for talking to the Python backend.

async function check(response) {
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      message = (await response.json()).detail ?? message;
    } catch {
      // the error had no JSON body - keep the status text
    }
    throw new Error(message);
  }
  return response.json();
}

export async function listRoms() {
  return check(await fetch("/api/roms"));
}

export async function uploadRom(file) {
  const form = new FormData();
  form.append("file", file);
  return check(await fetch("/api/roms", { method: "POST", body: form }));
}

export async function deleteRom(id) {
  return check(await fetch(`/api/roms/${id}`, { method: "DELETE" }));
}

// Open a live game. Returns the WebSocket; frames arrive as binary messages.
export function openPlaySocket(romId) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/play/${romId}`);
  socket.binaryType = "arraybuffer";
  return socket;
}
