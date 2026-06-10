from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from database import query
from data import KNOCKOUT_FIXTURE
from flags import flag_url

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/bracket", response_class=HTMLResponse)
async def bracket_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    results = query("SELECT * FROM results")
    results_by_num = {r["match_numero"]: r for r in results}

    def build_match(num, fecha, fase, pos1, pos2):
        r = results_by_num.get(num)
        local_name = r["local"] if r else None
        vis_name = r["visitante"] if r else None
        return {
            "numero": num,
            "fecha": fecha,
            "fase": fase,
            "local_label": local_name or pos1,
            "visitante_label": vis_name or pos2,
            "flag_local": flag_url(local_name) if local_name else "",
            "flag_visitante": flag_url(vis_name) if vis_name else "",
            "resultado": r,
        }

    bracket = {"r32": [], "r16": [], "qf": [], "sf": [], "tp": [], "f": []}
    fase_key = {
        "Ronda de 32": "r32", "Octavos": "r16", "Cuartos": "qf",
        "Semifinal": "sf", "Tercer lugar": "tp", "Final": "f"
    }

    for num, fecha, fase, pos1, pos2 in KNOCKOUT_FIXTURE:
        key = fase_key.get(fase)
        if key:
            bracket[key].append(build_match(num, fecha, fase, pos1, pos2))

    return templates.TemplateResponse("bracket.html", {
        "request": request,
        "user": user,
        "bracket": bracket,
    })
