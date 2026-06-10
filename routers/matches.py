from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from database import query, execute
from data import MATCHES_BY_NUM, TEAMS
import httpx, os

router = APIRouter()
templates = Jinja2Templates(directory="templates")
PHASES = ["Grupos","Ronda de 32","Octavos","Cuartos","Semifinal","Tercer lugar","Final"]

@router.get("/matches", response_class=HTMLResponse)
async def matches_page(request: Request, phase: str = "Grupos"):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    results = query("SELECT * FROM results")
    results_by_num = {r["match_numero"]: r for r in results}

    match_list = [m.copy() for m in MATCHES_BY_NUM.values() if m["fase"] == phase]
    for m in match_list:
        m["resultado"] = results_by_num.get(m["numero"])

    match_list.sort(key=lambda x: (x.get("fecha", ""), x["numero"]))

    return templates.TemplateResponse("matches.html", {
        "request": request,
        "user": user,
        "matches": match_list,
        "phases": PHASES,
        "current_phase": phase,
    })

@router.get("/admin/sync-results")
async def sync_results(request: Request):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    await _fetch_and_store_results()
    return RedirectResponse("/matches", status_code=302)

async def _fetch_and_store_results():
    api_key = os.environ.get("FOOTBALL_API_KEY", "")
    if not api_key:
        return
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.football-data.org/v4/competitions/WC/matches",
            headers={"X-Auth-Token": api_key},
            timeout=10
        )
        if resp.status_code != 200:
            return
        data = resp.json()
        fase_map = {
            "GROUP_STAGE": "Grupos", "ROUND_OF_32": "Ronda de 32",
            "ROUND_OF_16": "Octavos", "QUARTER_FINALS": "Cuartos",
            "SEMI_FINALS": "Semifinal", "THIRD_PLACE": "Tercer lugar", "FINAL": "Final",
        }
        for m in data.get("matches", []):
            if m["status"] != "FINISHED":
                continue
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            score = m["score"]["fullTime"]
            fase = fase_map.get(m["stage"], m["stage"])
            gl = score.get("home") or 0
            gv = score.get("away") or 0
            winner = m.get("score", {}).get("winner")

            match_num = m["id"]
            for num, match in MATCHES_BY_NUM.items():
                if match["local"] == home and match["visitante"] == away:
                    match_num = num
                    break

            local_team = TEAMS.get(home)
            away_team = TEAMS.get(away)
            pts_local = pts_visitante = 0.0

            if fase == "Grupos" and local_team and away_team:
                if gl > gv: pts_local = local_team["pts_victoria"]
                elif gl == gv:
                    pts_local = local_team["pts_empate"]
                    pts_visitante = away_team["pts_empate"]
                else: pts_visitante = away_team["pts_victoria"]
            else:
                if winner == "HOME_TEAM" and local_team:
                    pts_local = local_team["pts_victoria"]
                elif winner == "AWAY_TEAM" and away_team:
                    pts_visitante = away_team["pts_victoria"]

            avanza = "local" if winner == "HOME_TEAM" else "visitante" if winner == "AWAY_TEAM" else None

            execute("""
                INSERT INTO results (match_numero, fase, local, visitante, goles_local, goles_visitante, avanza, pts_local, pts_visitante)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_numero) DO UPDATE SET
                    goles_local=EXCLUDED.goles_local, goles_visitante=EXCLUDED.goles_visitante,
                    avanza=EXCLUDED.avanza, pts_local=EXCLUDED.pts_local, pts_visitante=EXCLUDED.pts_visitante
            """, (match_num, fase, home, away, gl, gv, avanza, pts_local, pts_visitante))
