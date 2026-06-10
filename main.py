import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from routers import auth, draft, standings, matches
from routers.my_teams import router as my_teams_router
from routers.bracket import router as bracket_router

app = FastAPI(title="Quiniela Mundial 2026")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "quiniela2026-secret"),
    max_age=60 * 60 * 24 * 7,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Add enumerate to Jinja2
templates = Jinja2Templates(directory="templates")
templates.env.globals["enumerate"] = enumerate

app.include_router(auth.router)
app.include_router(draft.router)
app.include_router(standings.router)
app.include_router(matches.router)
app.include_router(my_teams_router)
app.include_router(bracket_router)
