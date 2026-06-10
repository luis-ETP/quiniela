from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from database import query
from data import TEAMS
from flags import flag_url

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/mis-equipos", response_class=HTMLResponse)
async def mis_equipos(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    picks = query(
        "SELECT * FROM picks WHERE participant_username = %s",
        (user["username"],)
    )
    results = query("SELECT * FROM results")

    # Build pts per team
    pts_by_team = {}
    vic_by_team = {}
    emp_by_team = {}
    for r in results:
        local = r.get("local", "")
        visitante = r.get("visitante", "")
        gl = r.get("goles_local") or 0
        gv = r.get("goles_visitante") or 0

        for team, side in [(local, "local"), (visitante, "visitante")]:
            if team not in pts_by_team:
                pts_by_team[team] = 0.0
                vic_by_team[team] = 0
                emp_by_team[team] = 0
            pts = float(r.get(f"pts_{side}") or 0)
            pts_by_team[team] += pts
            if r["fase"] == "Grupos":
                if side == "local":
                    if gl > gv: vic_by_team[team] += 1
                    elif gl == gv: emp_by_team[team] += 1
                else:
                    if gv > gl: vic_by_team[team] += 1
                    elif gv == gl: emp_by_team[team] += 1
            elif r.get("avanza") == side:
                vic_by_team[team] += 1

    picks_by_bombo = {}
    for p in picks:
        tname = p["team_nombre"]
        team = TEAMS.get(tname, {})
        picks_by_bombo[p["bombo"]] = {
            "nombre": tname,
            "grupo": team.get("grupo", ""),
            "ranking_fifa": team.get("ranking_fifa", ""),
            "bombo": p["bombo"],
            "flag_url": flag_url(tname),
            "pts": round(pts_by_team.get(tname, 0), 2),
            "victorias": vic_by_team.get(tname, 0),
            "empates": emp_by_team.get(tname, 0),
        }

    pts_total = sum(t["pts"] for t in picks_by_bombo.values())
    pts_cd = sum(t["pts"] for b, t in picks_by_bombo.items() if b in ("C", "D"))
    total_victorias = sum(t["victorias"] for t in picks_by_bombo.values())
    total_empates = sum(t["empates"] for t in picks_by_bombo.values())

    return templates.TemplateResponse("mis_equipos.html", {
        "request": request,
        "user": user,
        "picks": picks,
        "picks_by_bombo": picks_by_bombo,
        "pts_total": round(pts_total, 2),
        "pts_cd": round(pts_cd, 2),
        "total_victorias": total_victorias,
        "total_empates": total_empates,
    })
