from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from database import query, execute
from data import MATCHES_BY_NUM, TEAMS, KNOCKOUT_FIXTURE
from flags import flag_url, normalize
import httpx, os

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PHASES = ["Grupos","Ronda de 32","Octavos","Cuartos","Semifinal","Tercer lugar","Final"]

STAGE_MAP = {
    "GROUP_STAGE": "Grupos", "ROUND_OF_32": "Ronda de 32",
    "ROUND_OF_16": "Octavos", "QUARTER_FINALS": "Cuartos",
    "SEMI_FINALS": "Semifinal", "THIRD_PLACE": "Tercer lugar", "FINAL": "Final",
}


def get_team_owners():
    """Returns dict: team_nombre -> username"""
    picks = query("SELECT participant_username, team_nombre FROM picks")
    return {p["team_nombre"]: p["participant_username"] for p in picks}


def get_or_create_duelo(match_num, local, visitante, owner_local, owner_visitante):
    """Get existing duelo or create one."""
    existing = query("SELECT * FROM duelos WHERE match_numero = %s", (match_num,))
    if existing:
        return existing[0]
    execute("""
        INSERT INTO duelos (match_numero, owner1_username, owner2_username, team1, team2)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (match_numero) DO NOTHING
    """, (match_num, owner_local, owner_visitante, local, visitante))
    result = query("SELECT * FROM duelos WHERE match_numero = %s", (match_num,))
    return result[0] if result else None


def update_duelo_winner(match_num, avanza, owner_local, owner_visitante):
    """Update duelo winner based on match result."""
    if avanza == "local":
        winner = owner_local
    elif avanza == "visitante":
        winner = owner_visitante
    else:
        winner = None
    if winner:
        execute("UPDATE duelos SET ganador_username = %s WHERE match_numero = %s",
                (winner, match_num))


@router.get("/matches", response_class=HTMLResponse)
async def matches_page(request: Request, phase: str = "Grupos"):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    try:
        await _sync_results()
    except Exception:
        pass

    results = query("SELECT * FROM results ORDER BY match_numero")
    results_by_num = {r["match_numero"]: r for r in results}
    duelos_by_num = {d["match_numero"]: d for d in query("SELECT * FROM duelos")}
    owners = get_team_owners()

    if phase == "Grupos":
        match_list = []
        for m in sorted(MATCHES_BY_NUM.values(), key=lambda x: (x["fecha"], x["numero"])):
            if m["fase"] != "Grupos":
                continue
            mc = m.copy()
            mc["resultado"] = results_by_num.get(m["numero"])
            mc["flag_local"] = flag_url(m["local"])
            mc["flag_visitante"] = flag_url(m["visitante"])
            # Check if both teams have owners → duelo
            owner_local = owners.get(m["local"])
            owner_visitante = owners.get(m["visitante"])
            if owner_local and owner_visitante and owner_local != owner_visitante:
                mc["duelo"] = get_or_create_duelo(
                    m["numero"], m["local"], m["visitante"], owner_local, owner_visitante)
                # Update winner if match finished
                r = mc["resultado"]
                if r and r.get("avanza") and mc["duelo"] and not mc["duelo"].get("ganador_username"):
                    update_duelo_winner(m["numero"], r["avanza"], owner_local, owner_visitante)
                    mc["duelo"] = query("SELECT * FROM duelos WHERE match_numero = %s", (m["numero"],))
                    mc["duelo"] = mc["duelo"][0] if mc["duelo"] else None
            else:
                mc["duelo"] = None
            mc["owner_local"] = owner_local
            mc["owner_visitante"] = owner_visitante
            match_list.append(mc)
    else:
        match_list = []
        for num, fecha, fase, pos1, pos2 in KNOCKOUT_FIXTURE:
            if fase != phase:
                continue
            r = results_by_num.get(num)
            local_name = r["local"] if r else None
            vis_name = r["visitante"] if r else None
            owner_local = owners.get(local_name) if local_name else None
            owner_visitante = owners.get(vis_name) if vis_name else None
            duelo = None
            if owner_local and owner_visitante and owner_local != owner_visitante:
                duelo = get_or_create_duelo(num, local_name, vis_name, owner_local, owner_visitante)
                if r and r.get("avanza") and duelo and not duelo.get("ganador_username"):
                    update_duelo_winner(num, r["avanza"], owner_local, owner_visitante)
                    d = query("SELECT * FROM duelos WHERE match_numero = %s", (num,))
                    duelo = d[0] if d else duelo
            match_list.append({
                "numero": num,
                "fecha": fecha,
                "fase": fase,
                "grupo": "",
                "local": local_name or pos1,
                "visitante": vis_name or pos2,
                "local_label": local_name or pos1,
                "visitante_label": vis_name or pos2,
                "es_fixture": not bool(r),
                "flag_local": flag_url(local_name) if local_name else "",
                "flag_visitante": flag_url(vis_name) if vis_name else "",
                "resultado": r,
                "duelo": duelo,
                "owner_local": owner_local,
                "owner_visitante": owner_visitante,
            })
        match_list.sort(key=lambda x: (x["fecha"], x["numero"]))

    # Get user names for display
    from data import USERS
    user_names = {u: d["nombre"] for u, d in USERS.items()}

    return templates.TemplateResponse("matches.html", {
        "request": request,
        "user": user,
        "matches": match_list,
        "phases": PHASES,
        "current_phase": phase,
        "is_grupos": phase == "Grupos",
        "user_names": user_names,
    })


@router.post("/duelo/{match_num}/apuesta")
async def set_apuesta(request: Request, match_num: int, monto: float = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    duelo = query("SELECT * FROM duelos WHERE match_numero = %s", (match_num,))
    if not duelo:
        return RedirectResponse("/matches", status_code=302)
    duelo = duelo[0]

    # Only the owners can bet
    if user["username"] == duelo["owner1_username"]:
        execute("UPDATE duelos SET apuesta1 = %s WHERE match_numero = %s", (monto, match_num))
    elif user["username"] == duelo["owner2_username"]:
        execute("UPDATE duelos SET apuesta2 = %s WHERE match_numero = %s", (monto, match_num))

    # Redirect back to correct phase
    from data import MATCHES_BY_NUM as MBN
    fase = "Grupos"
    if match_num in MBN:
        fase = MBN[match_num]["fase"]
    else:
        result = query("SELECT fase FROM results WHERE match_numero = %s", (match_num,))
        if result:
            fase = result[0]["fase"]
    return RedirectResponse(f"/matches?phase={fase}", status_code=302)


@router.get("/admin/sync-results")
async def sync_results_get(request: Request):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    await _sync_results()
    return RedirectResponse("/matches", status_code=302)


@router.get("/admin/api-check")
async def api_check(request: Request):
    from fastapi.responses import JSONResponse
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    api_key = os.environ.get("FOOTBALL_API_KEY", "")
    async with httpx.AsyncClient(timeout=10) as client:
        r2 = await client.get(
            "https://api.football-data.org/v4/competitions/WC/matches",
            headers={"X-Auth-Token": api_key},
        )
        return JSONResponse({"status": r2.status_code, "preview": r2.text[:800]})


async def _sync_results():
    api_key = os.environ.get("FOOTBALL_API_KEY", "")
    if not api_key:
        return
    async with httpx.AsyncClient(timeout=8) as client:
        resp = await client.get(
            "https://api.football-data.org/v4/competitions/WC/matches",
            headers={"X-Auth-Token": api_key},
        )
        if resp.status_code != 200:
            return
        data = resp.json()
        for m in data.get("matches", []):
            if m["status"] not in ("FINISHED", "IN_PLAY", "PAUSED"):
                continue
            home = normalize(m["homeTeam"]["name"])
            away = normalize(m["awayTeam"]["name"])
            score = m["score"]["fullTime"]
            fase = STAGE_MAP.get(m["stage"], m["stage"])
            gl = score.get("home")
            gv = score.get("away")
            finished = m["status"] == "FINISHED"
            winner = m["score"].get("winner") if finished else None

            match_num = m["id"]
            for num, match in MATCHES_BY_NUM.items():
                if match["local"] == home and match["visitante"] == away:
                    match_num = num
                    break

            local_team = TEAMS.get(home)
            away_team = TEAMS.get(away)
            pts_local = pts_visitante = 0.0

            if finished and gl is not None and gv is not None:
                if fase == "Grupos" and local_team and away_team:
                    if gl > gv: pts_local = float(local_team["pts_victoria"])
                    elif gl == gv:
                        pts_local = float(local_team["pts_empate"])
                        pts_visitante = float(away_team["pts_empate"])
                    else: pts_visitante = float(away_team["pts_victoria"])
                elif fase != "Grupos":
                    if winner == "HOME_TEAM" and local_team:
                        pts_local = float(local_team["pts_victoria"])
                    elif winner == "AWAY_TEAM" and away_team:
                        pts_visitante = float(away_team["pts_victoria"])

            avanza = None
            if winner == "HOME_TEAM": avanza = "local"
            elif winner == "AWAY_TEAM": avanza = "visitante"

            execute("""
                INSERT INTO results
                    (match_numero, fase, local, visitante, goles_local, goles_visitante,
                     avanza, pts_local, pts_visitante)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (match_numero) DO UPDATE SET
                    local=EXCLUDED.local, visitante=EXCLUDED.visitante,
                    goles_local=EXCLUDED.goles_local, goles_visitante=EXCLUDED.goles_visitante,
                    avanza=EXCLUDED.avanza, pts_local=EXCLUDED.pts_local,
                    pts_visitante=EXCLUDED.pts_visitante
            """, (match_num, fase, home, away, gl, gv, avanza, pts_local, pts_visitante))
