"""Standalone app for the voice routes, until the team wires one shared FastAPI app.

Run from the repo root:   uv run fastapi dev voice/dev_app.py --port 8000
To merge into the shared app later:
    from voice.router import router as voice_router
    app.include_router(voice_router)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from voice.router import router as voice_router

app = FastAPI(title="Tell Us Once — voice")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(voice_router)
