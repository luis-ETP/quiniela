import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from routers import auth, draft, standings, matches

app = FastAPI(title="Quiniela Mundial 2026")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "quiniela2026-secret"),
    max_age=60 * 60 * 24 * 7,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth.router)
app.include_router(draft.router)
app.include_router(standings.router)
app.include_router(matches.router)
