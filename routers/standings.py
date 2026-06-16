from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from database import query
from data import USERS, TEAMS
from routers.pronosticos import get_total_bonus_by_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def standings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    picks = query("SELECT * FROM picks")
    results = query("SELECT * FROM results")

    picks_by_user = {}
    for p in picks:
        picks_by_user.setdefault(p["participant_username"], []).append(p)

    standings = []
    for uname, udata in USERS.items():
        if udata.get("is_admin"):
            continue
        my_picks = picks_by_user.get(uname, [])
        my_teams = {p["team_nombre"]: TEAMS.get(p["team_nombre"]) for p in my_picks if TEAMS.get(p["team_nombre"])}
        teams_by_bombo = {}
        for tname, t in my_teams.items():
            if t:
                teams_by_bombo[t["bombo"]] = t

        pts_total = 0.0
        victorias = 0
        empates = 0
        derrotas = 0
        pts_by_team = {t: 0.0 for t in my_teams}

        for r in results:
            local = r.get("local", "")
            visitante = r.get("visitante", "")
            gl = r.get("goles_local") or 0
            gv = r.get("goles_visitante") or 0

            finished = r.get("goles_local") is not None and r.get("goles_visitante") is not None

            if local in my_teams:
                pts = float(r.get("pts_local") or 0)
                pts_by_team[local] = pts_by_team.get(local, 0) + pts
                pts_total += pts
                if finished and r["fase"] == "Grupos":
                    if gl > gv: victorias += 1
                    elif gl == gv: empates += 1
                    else: derrotas += 1
                elif finished and r.get("avanza") == "local": victorias += 1
                elif finished and r.get("avanza") == "visitante": derrotas += 1

            if visitante in my_teams:
                pts = float(r.get("pts_visitante") or 0)
                pts_by_team[visitante] = pts_by_team.get(visitante, 0) + pts
                pts_total += pts
                if finished and r["fase"] == "Grupos":
                    if gv > gl: victorias += 1
                    elif gv == gl: empates += 1
                    else: derrotas += 1
                elif finished and r.get("avanza") == "visitante": victorias += 1
                elif finished and r.get("avanza") == "local": derrotas += 1

        pts_cd = sum(pts_by_team.get(t, 0) for t, td in my_teams.items() if td and td["bombo"] in ("C", "D"))
        pts_d  = sum(pts_by_team.get(t, 0) for t, td in my_teams.items() if td and td["bombo"] == "D")

        # Per-team V/E/P stats
        team_stats = {}
        for tname in my_teams:
            tv = ve = tp = 0
            for r in results:
                local = r.get("local", "")
                visitante = r.get("visitante", "")
                gl = r.get("goles_local")
                gv = r.get("goles_visitante")
                if gl is None or gv is None:
                    continue
                gl, gv = int(gl), int(gv)
                if local == tname:
                    if r["fase"] == "Grupos":
                        if gl > gv: tv += 1
                        elif gl == gv: ve += 1
                        else: tp += 1
                    elif r.get("avanza") == "local": tv += 1
                    elif r.get("avanza") == "visitante": tp += 1
                elif visitante == tname:
                    if r["fase"] == "Grupos":
                        if gv > gl: tv += 1
                        elif gv == gl: ve += 1
                        else: tp += 1
                    elif r.get("avanza") == "visitante": tv += 1
                    elif r.get("avanza") == "local": tp += 1
            team_stats[tname] = {"v": tv, "e": ve, "p": tp}

        standings.append({
            "username": uname,
            "nombre": udata["nombre"],
            "teams_by_bombo": teams_by_bombo,
            "pts_by_team": pts_by_team,
            "pts_total": round(pts_total, 2),
            "victorias": victorias,
            "empates": empates,
            "derrotas": derrotas,
            "pts_cd": round(pts_cd, 2),
            "pts_d": round(pts_d, 2),
            "team_stats": team_stats,
            "lineup_completo": len(my_picks) == 4,
        })

    bonus_by_user = get_total_bonus_by_user()
    for s in standings:
        s["bonus"] = round(bonus_by_user.get(s["username"], 0), 2)
        s["pts_total_con_bonus"] = round(s["pts_total"] + s["bonus"], 2)

    standings.sort(key=lambda x: (-x["pts_total_con_bonus"], -x["victorias"], -x["pts_cd"], -x["pts_d"]))
    for i, s in enumerate(standings):
        s["posicion"] = i + 1

    return templates.TemplateResponse("standings.html", {
        "request": request,
        "user": user,
        "standings": standings,
        "finalizados": len(results),
        "pagados": 0,
    })
