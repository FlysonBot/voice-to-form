"""The combined backend: every role's routes in one FastAPI app.

Run from the repo root:   uv run uvicorn server.main:app --reload --port 8000
The frontend (npm run dev in frontend/) forwards /api/* here (frontend/vite.config.ts).

Route owners (API.md):
  /onboarding/turn, /voice/answer   P2 gemini/   (via server/adapters.py for the frontend's shape)
  /voice/question, /recap           P3 voice/    (via server/adapters.py)
  /recap/correct, /voice/tts        P3 voice/
  /form/fill                        P1 form_engine/
  /form/gaps                        server/adapters.py (from P1's fields.json)
"""

import logging

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from form_engine.routes import router as form_router  # noqa: E402
from server.adapters import router as adapters_router  # noqa: E402
from voice.router import router as voice_router  # noqa: E402

# Routes the adapters serve; the role routers' own versions of these are not mounted.
ADAPTED = {r.path for r in adapters_router.routes}


def _without(router: APIRouter, paths: set[str]) -> APIRouter:
    out = APIRouter()
    out.routes.extend(r for r in router.routes if getattr(r, "path", None) not in paths)
    return out


app = FastAPI(title="Tell Us Once")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(adapters_router)
app.include_router(_without(voice_router, ADAPTED))
app.include_router(form_router)


@app.get("/health")
def health():
    return {"ok": True}
