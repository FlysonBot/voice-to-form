"""One-port launcher: built frontend at /, API at /api (what the frontend calls).

    cd frontend && VITE_API_MODE=live npm run build && cd ..
    uv run uvicorn server.serve:app --port 8080
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.main import app as api

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app = FastAPI(title="Tell Us Once (app)")
app.mount("/api", api)
app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/{path:path}")
def spa(path: str):
    """Real files from dist/, otherwise index.html (React Router handles /onboarding, /form/...)."""
    f = (DIST / path).resolve()
    if path and f.is_file() and DIST in f.parents:
        return FileResponse(f)
    return FileResponse(DIST / "index.html")
