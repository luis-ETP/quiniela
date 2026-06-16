from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from data import TEAMS_BY_RANKING
from flags import flag_url

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/reglas", response_class=HTMLResponse)
async def reglas_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    teams_by_bombo = {"A": [], "B": [], "C": [], "D": []}
    for t in TEAMS_BY_RANKING:
        teams_by_bombo[t["bombo"]].append({**t, "flag_url": flag_url(t["nombre"])})

    return templates.TemplateResponse("reglas.html", {
        "request": request,
        "user": user,
        "teams_by_bombo": teams_by_bombo,
    })
