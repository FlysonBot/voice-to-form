"""Standalone app to run just the gemini/ endpoints during development:

    uv run fastapi dev gemini/dev_app.py

The team's combined app should mount `gemini.router.router` instead of using this file.
"""

import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from gemini.router import router

app = FastAPI(title="Tell Us Once - gemini (dev)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True}
