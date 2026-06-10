from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from database import get_db
from data import USERS, TEAMS

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def standings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    db = get_db()
    picks = db.table("picks").select("*").execute().data
    results = db.table("results").select("*").execute().data

    picks_by_user = {}
    for p in picks:
        u = p["participant_username"]
        picks_by_user.setdefault(u, []).append(p)

    standings = []
    for uname, udata in USERS.items():
        if udata.get("is_admin"):
            continue
        my_picks = picks_by_user.get(uname, [])
        my_teams = {p["team_nombre"]: TEAMS.get(p["team_nombre"]) for p in my_picks if TEAMS.get(p["team_nombre"])}
        teams_by_bombo = {}
        for tname, t in my_teams.items():
            teams_by_bombo[t["bombo"]] = t

        pts_total = 0.0
        victorias = 0
        empates = 0
        pts_by_team = {t: 0.0 for t in my_teams}

        for r in results:
            local = r.get("local","")
            visitante = r.get("visitante","")
            gl = r.get("goles_local") or 0
            gv = r.get("goles_visitante") or 0

            if local in my_teams:
                pts = float(r.get("pts_local") or 0)
                pts_by_team[local] = pts_by_team.get(local,0) + pts
                pts_total += pts
                if r["fase"] == "Grupos":
                    if gl > gv: victorias += 1
                    elif gl == gv: empates += 1
                elif r.get("avanza") == "local": victorias += 1

            if visitante in my_teams:
                pts = float(r.get("pts_visitante") or 0)
                pts_by_team[visitante] = pts_by_team.get(visitante,0) + pts
                pts_total += pts
                if r["fase"] == "Grupos":
                    if gv > gl: victorias += 1
                    elif gv == gl: empates += 1
                elif r.get("avanza") == "visitante": victorias += 1

        pts_cd = sum(pts_by_team.get(t,0) for t,td in my_teams.items() if td and td["bombo"] in ("C","D"))
        pts_d  = sum(pts_by_team.get(t,0) for t,td in my_teams.items() if td and td["bombo"] == "D")

        standings.append({
            "username": uname,
            "nombre": udata["nombre"],
            "teams_by_bombo": teams_by_bombo,
            "pts_by_team": pts_by_team,
            "pts_total": round(pts_total,2),
            "victorias": victorias,
            "empates": empates,
            "pts_cd": round(pts_cd,2),
            "pts_d": round(pts_d,2),
            "lineup_completo": len(my_picks) == 4,
        })

    standings.sort(key=lambda x: (-x["pts_total"],-x["victorias"],-x["pts_cd"],-x["pts_d"]))
    for i,s in enumerate(standings):
        s["posicion"] = i+1

    return templates.TemplateResponse("standings.html", {
        "request": request,
        "user": user,
        "standings": standings,
        "finalizados": len(results),
        "pagados": 0,
    })
