from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_admin_client
from auth import get_current_user, USERS

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def standings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    sb = get_admin_client()
    profiles = sb.table("profiles").select("*").execute().data
    picks = sb.table("picks").select("*, teams(*)").execute().data
    matches = sb.table("matches").select("*").eq("estado", "Finalizado").execute().data

    standings = []
    for p in profiles:
        uname = p["username"]
        my_picks = [pk for pk in picks if pk["participant_username"] == uname]
        my_teams = [pk["teams"] for pk in my_picks if pk.get("teams")]
        team_ids = {t["id"] for t in my_teams if t}

        pts_total = 0.0
        victorias = 0
        empates = 0
        pts_by_team = {}

        for match in matches:
            lid = match.get("local_id")
            vid = match.get("visitante_id")
            gl = match.get("goles_local") or 0
            gv = match.get("goles_visitante") or 0

            if lid in team_ids:
                pts = float(match.get("pts_local") or 0)
                pts_by_team[lid] = pts_by_team.get(lid, 0) + pts
                pts_total += pts
                if match["fase"] == "Grupos":
                    if gl > gv: victorias += 1
                    elif gl == gv: empates += 1
                elif match.get("equipo_avanza_id") == lid:
                    victorias += 1

            if vid in team_ids:
                pts = float(match.get("pts_visitante") or 0)
                pts_by_team[vid] = pts_by_team.get(vid, 0) + pts
                pts_total += pts
                if match["fase"] == "Grupos":
                    if gv > gl: victorias += 1
                    elif gv == gl: empates += 1
                elif match.get("equipo_avanza_id") == vid:
                    victorias += 1

        pts_cd = sum(pts_by_team.get(t["id"], 0) for t in my_teams if t and t.get("bombo") in ("C","D"))
        pts_d = sum(pts_by_team.get(t["id"], 0) for t in my_teams if t and t.get("bombo") == "D")

        teams_by_bombo = {}
        for pk in my_picks:
            t = pk.get("teams")
            if t:
                teams_by_bombo[t.get("bombo","?")] = t

        standings.append({
            "profile": p,
            "teams_by_bombo": teams_by_bombo,
            "pts_total": round(pts_total, 2),
            "victorias": victorias,
            "empates": empates,
            "pts_cd": round(pts_cd, 2),
            "pts_d": round(pts_d, 2),
            "pts_by_team": pts_by_team,
            "desempate": p.get("desempate_manual") or 0,
            "lineup_completo": len(my_teams) == 4,
        })

    standings.sort(key=lambda x: (-x["pts_total"], -x["victorias"], -x["pts_cd"], -x["pts_d"], x["desempate"]))
    for i, s in enumerate(standings):
        s["posicion"] = i + 1

    return templates.TemplateResponse("standings.html", {
        "request": request,
        "user": user,
        "standings": standings,
        "finalizados": len(matches),
        "pagados": sum(1 for p in profiles if p.get("pagado")),
    })
