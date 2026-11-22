"""
Start the CHIP-8 RL web server.

Run from the backend folder:   python serve.py
Then open http://localhost:8000 (after building the frontend), or use the
frontend's development server at http://localhost:5173.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
