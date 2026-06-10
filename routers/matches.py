from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from database import get_db
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

    db = get_db()
    results = db.table("results").select("*").execute().data
    results_by_num = {r["match_numero"]: r for r in results}

    if phase == "Grupos":
        match_list = [m for m in MATCHES_BY_NUM.values() if m["fase"] == "Grupos"]
    else:
        match_list = [m for m in MATCHES_BY_NUM.values() if m["fase"] == phase]
        # For knockout, also show from results table
        ko_results = [r for r in results if r.get("fase") == phase]
        ko_nums = {r["match_numero"] for r in ko_results}
        for r in ko_results:
            if r["match_numero"] not in MATCHES_BY_NUM:
                match_list.append({
                    "numero": r["match_numero"],
                    "fecha": r.get("fecha",""),
                    "fase": phase,
                    "grupo": "",
                    "local": r.get("local",""),
                    "visitante": r.get("visitante",""),
                })

    for m in match_list:
        r = results_by_num.get(m["numero"])
        m["resultado"] = r

    match_list.sort(key=lambda x: (x.get("fecha",""), x["numero"]))

    return templates.TemplateResponse("matches.html", {
        "request": request,
        "user": user,
        "matches": match_list,
        "phases": PHASES,
        "current_phase": phase,
    })

@router.post("/admin/sync-results")
async def sync_results(request: Request):
    require_admin = get_current_user(request)
    if not require_admin or not require_admin.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    await _fetch_and_store_results()
    return RedirectResponse("/matches", status_code=302)

async def _fetch_and_store_results():
    api_key = os.environ.get("FOOTBALL_API_KEY","")
    if not api_key:
        return
    db = get_db()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.football-data.org/v4/competitions/WC/matches",
            headers={"X-Auth-Token": api_key},
            timeout=10
        )
        if resp.status_code != 200:
            return
        data = resp.json()
        for m in data.get("matches", []):
            if m["status"] != "FINISHED":
                continue
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            score = m["score"]["fullTime"]
            fase_map = {
                "GROUP_STAGE": "Grupos",
                "ROUND_OF_32": "Ronda de 32",
                "ROUND_OF_16": "Octavos",
                "QUARTER_FINALS": "Cuartos",
                "SEMI_FINALS": "Semifinal",
                "THIRD_PLACE": "Tercer lugar",
                "FINAL": "Final",
            }
            fase = fase_map.get(m["stage"], m["stage"])
            match_num = m["id"]  # use API id as numero for knockout

            # Find match number from our data
            for num, match in MATCHES_BY_NUM.items():
                if match["local"] == home and match["visitante"] == away:
                    match_num = num
                    break

            # Calculate pts
            local_team = TEAMS.get(home)
            away_team = TEAMS.get(away)
            gl = score.get("home") or 0
            gv = score.get("away") or 0
            avanza = m.get("score",{}).get("winner")  # HOME_TEAM or AWAY_TEAM

            pts_local = 0.0
            pts_visitante = 0.0
            if fase == "Grupos" and local_team and away_team:
                if gl > gv: pts_local = local_team["pts_victoria"]
                elif gl == gv:
                    pts_local = local_team["pts_empate"]
                    pts_visitante = away_team["pts_empate"]
                else: pts_visitante = away_team["pts_victoria"]
            else:
                if avanza == "HOME_TEAM" and local_team:
                    pts_local = local_team["pts_victoria"]
                elif avanza == "AWAY_TEAM" and away_team:
                    pts_visitante = away_team["pts_victoria"]

            db.table("results").upsert({
                "match_numero": match_num,
                "fase": fase,
                "local": home,
                "visitante": away,
                "goles_local": gl,
                "goles_visitante": gv,
                "avanza": "local" if avanza=="HOME_TEAM" else "visitante" if avanza=="AWAY_TEAM" else None,
                "pts_local": pts_local,
                "pts_visitante": pts_visitante,
            }, on_conflict="match_numero").execute()
