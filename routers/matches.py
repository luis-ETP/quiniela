from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from database import query, execute
from data import MATCHES_BY_NUM, TEAMS, KNOCKOUT_FIXTURE, KICKOFF_CDMX
from flags import flag_url, normalize
from routers.pronosticos import calc_bonus
import httpx, os
from datetime import datetime
import pytz

router = APIRouter()
templates = Jinja2Templates(directory="templates")
CDMX = pytz.timezone("America/Mexico_City")

PHASES = ["Grupos","Ronda de 32","Octavos","Cuartos","Semifinal","Tercer lugar","Final"]

STAGE_MAP = {
    "GROUP_STAGE": "Grupos", "ROUND_OF_32": "Ronda de 32",
    "ROUND_OF_16": "Octavos", "QUARTER_FINALS": "Cuartos",
    "SEMI_FINALS": "Semifinal", "THIRD_PLACE": "Tercer lugar", "FINAL": "Final",
}

def is_match_locked(match_num):
    ks = KICKOFF_CDMX.get(match_num)
    if not ks:
        return False
    return datetime.now(CDMX) >= CDMX.localize(datetime.fromisoformat(ks))

def get_team_owners():
    picks = query("SELECT participant_username, team_nombre FROM picks")
    return {p["team_nombre"]: p["participant_username"] for p in picks}

def get_or_create_duelo(match_num, local, visitante, owner_local, owner_visitante, all_duelos):
    if match_num in all_duelos:
        return all_duelos[match_num]
    execute("""INSERT INTO duelos (match_numero, owner1_username, owner2_username, team1, team2)
        VALUES (%s,%s,%s,%s,%s) ON CONFLICT (match_numero) DO NOTHING""",
        (match_num, owner_local, owner_visitante, local, visitante))
    d = query("SELECT * FROM duelos WHERE match_numero = %s", (match_num,))
    return d[0] if d else None

def update_duelo_winner(match_num, avanza, owner_local, owner_visitante):
    winner = owner_local if avanza == "local" else owner_visitante if avanza == "visitante" else None
    if winner:
        execute("UPDATE duelos SET ganador_username = %s WHERE match_numero = %s", (winner, match_num))

@router.get("/matches", response_class=HTMLResponse)
async def matches_page(request: Request, phase: str = "Grupos"):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Auto-sync removed - use /admin/sync-results manually

    # ── Batch load everything once ────────────────────────────────────────────
    results = query("SELECT * FROM results ORDER BY match_numero")
    results_by_num = {r["match_numero"]: r for r in results}

    all_duelos = {d["match_numero"]: d for d in query("SELECT * FROM duelos")}
    owners = get_team_owners()

    # Batch load all pronosticos
    all_pros = query("SELECT * FROM pronosticos")
    pros_by_match = {}
    for p in all_pros:
        key = str(p["match_numero"])
        pros_by_match.setdefault(key, []).append(p)

    from data import USERS
    user_names = {u: d["nombre"] for u, d in USERS.items()}

    def build_match_extras(num, local, visitante, r):
        locked = is_match_locked(num)
        owner_local = owners.get(local)
        owner_visitante = owners.get(visitante)

        # Duelo
        duelo = None
        if owner_local and owner_visitante and owner_local != owner_visitante:
            duelo = all_duelos.get(num)
            if not duelo:
                duelo = get_or_create_duelo(num, local, visitante, owner_local, owner_visitante, all_duelos)
                if duelo:
                    all_duelos[num] = duelo
            if duelo and r and r.get("avanza") and not duelo.get("ganador_username"):
                update_duelo_winner(num, r["avanza"], owner_local, owner_visitante)
                duelo["ganador_username"] = owner_local if r["avanza"] == "local" else owner_visitante

        # Pronosticos
        match_pros = pros_by_match.get(str(num), [])
        if locked and r and r.get("goles_local") is not None:
            for p in match_pros:
                b = calc_bonus(p["goles_local"], p["goles_visitante"],
                               r["goles_local"], r["goles_visitante"])
                p["puntos_bonus"] = b

        mi_pro = next((p for p in match_pros if p["username"] == user["username"]), None)
        pronosticos = match_pros if locked else []

        return {
            "locked": locked,
            "kickoff": KICKOFF_CDMX.get(num, ""),
            "owner_local": owner_local,
            "owner_visitante": owner_visitante,
            "duelo": duelo,
            "mi_pronostico": mi_pro,
            "pronosticos": pronosticos,
        }

    if phase == "Grupos":
        # Batch create missing duelos
        duelo_candidates = [(m["numero"], m["local"], m["visitante"],
                             owners.get(m["local"]), owners.get(m["visitante"]))
                            for m in MATCHES_BY_NUM.values()
                            if m["fase"] == "Grupos"
                            and owners.get(m["local"]) and owners.get(m["visitante"])
                            and owners.get(m["local"]) != owners.get(m["visitante"])]

        existing_nums = set(all_duelos.keys())
        for num, local, vis, ol, ov in duelo_candidates:
            if num not in existing_nums:
                execute("""INSERT INTO duelos (match_numero, owner1_username, owner2_username, team1, team2)
                    VALUES (%s,%s,%s,%s,%s) ON CONFLICT (match_numero) DO NOTHING""",
                    (num, ol, ov, local, vis))

        all_duelos_fresh = {d["match_numero"]: d for d in query("SELECT * FROM duelos")}

        match_list = []
        for m in sorted(MATCHES_BY_NUM.values(), key=lambda x: (x["fecha"], x["numero"])):
            if m["fase"] != "Grupos":
                continue
            r = results_by_num.get(m["numero"])
            extras = build_match_extras(m["numero"], m["local"], m["visitante"], r)
            extras["duelo"] = all_duelos_fresh.get(m["numero"]) if (
                extras["owner_local"] and extras["owner_visitante"] and
                extras["owner_local"] != extras["owner_visitante"]) else None
            if extras["duelo"] and r and r.get("avanza") and not extras["duelo"].get("ganador_username"):
                ol = owners.get(m["local"])
                ov = owners.get(m["visitante"])
                update_duelo_winner(m["numero"], r["avanza"], ol, ov)
                extras["duelo"]["ganador_username"] = ol if r["avanza"] == "local" else ov
            mc = {**m, "resultado": r,
                  "flag_local": flag_url(m["local"]),
                  "flag_visitante": flag_url(m["visitante"]),
                  "current_username": user["username"],
                  **extras}
            match_list.append(mc)
    else:
        match_list = []
        for num, fecha, fase, pos1, pos2 in KNOCKOUT_FIXTURE:
            if fase != phase:
                continue
            r = results_by_num.get(num)
            local_name = r["local"] if r else None
            vis_name = r["visitante"] if r else None
            try:
                extras = build_match_extras(num, local_name or "", vis_name or "", r)
            except Exception as e:
                import sys, traceback
                print(f"ERROR in build_match_extras for match {num}: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                raise
            match_list.append({
                "numero": num, "fecha": fecha, "fase": fase, "grupo": "",
                "local": local_name or pos1, "visitante": vis_name or pos2,
                "local_label": local_name or pos1, "visitante_label": vis_name or pos2,
                "es_fixture": not bool(r),
                "flag_local": flag_url(local_name) if local_name else "",
                "flag_visitante": flag_url(vis_name) if vis_name else "",
                "resultado": r, "current_username": user["username"], **extras,
            })
        match_list.sort(key=lambda x: (x["fecha"], x["numero"]))

    # Today's matches - groups + knockout
    import pytz
    today = datetime.now(pytz.timezone("America/Mexico_City")).strftime("%Y-%m-%d")
    today_matches = []

    for m in sorted(MATCHES_BY_NUM.values(), key=lambda x: (KICKOFF_CDMX.get(x["numero"], "99:99"), x["numero"])):
        if m["fecha"] != today:
            continue
        r = results_by_num.get(m["numero"])
        extras = build_match_extras(m["numero"], m["local"], m["visitante"], r)
        mc = {**m, "resultado": r,
              "flag_local": flag_url(m["local"]),
              "flag_visitante": flag_url(m["visitante"]),
              "current_username": user["username"],
              **extras}
        today_matches.append(mc)

    for num, fecha, fase, pos1, pos2 in KNOCKOUT_FIXTURE:
        if fecha != today:
            continue
        r = results_by_num.get(num)
        local_name = r["local"] if r else None
        vis_name = r["visitante"] if r else None
        extras = build_match_extras(num, local_name or "", vis_name or "", r)
        today_matches.append({
            "numero": num, "fecha": fecha, "fase": fase, "grupo": "",
            "local": local_name or pos1, "visitante": vis_name or pos2,
            "es_fixture": not bool(r),
            "flag_local": flag_url(local_name) if local_name else "",
            "flag_visitante": flag_url(vis_name) if vis_name else "",
            "resultado": r, "current_username": user["username"],
            **extras,
        })

    today_matches.sort(key=lambda x: KICKOFF_CDMX.get(x["numero"], "99:99"))

    # Build bracket pairs for knockout phases
    BRACKET_MAP = {
        "Ronda de 32": {89: [74,77], 90: [73,75], 91: [76,78], 92: [79,80],
                        93: [82,83], 94: [81,84], 95: [86,88], 96: [85,87]},
        "Octavos":     {97: [89,90], 98: [93,94], 99: [91,92], 100: [95,96]},
        "Cuartos":     {101: [97,98], 102: [99,100]},
        "Semifinal":   {104: [101,102]},
    }

    bracket_pairs = []
    if phase in BRACKET_MAP and not is_grupos:
        matches_by_num = {m["numero"]: m for m in match_list}
        next_phase_matches = {}
        next_phases = {"Ronda de 32": "Octavos", "Octavos": "Cuartos",
                      "Cuartos": "Semifinal", "Semifinal": "Final"}
        next_phase = next_phases.get(phase)
        if next_phase:
            for num, fecha, fase, pos1, pos2 in KNOCKOUT_FIXTURE:
                if fase == next_phase:
                    r = results_by_num.get(num)
                    local_name = r["local"] if r else None
                    vis_name = r["visitante"] if r else None
                    extras = build_match_extras(num, local_name or "", vis_name or "", r)
                    next_phase_matches[num] = {
                        "numero": num, "fecha": fecha, "fase": fase, "grupo": "",
                        "local": local_name or pos1, "visitante": vis_name or pos2,
                        "es_fixture": not bool(r),
                        "flag_local": flag_url(local_name) if local_name else "",
                        "flag_visitante": flag_url(vis_name) if vis_name else "",
                        "resultado": r, "current_username": user["username"],
                        **extras,
                    }

        for next_num, prev_nums in sorted(BRACKET_MAP[phase].items()):
            left = [matches_by_num[n] for n in prev_nums if n in matches_by_num]
            right = next_phase_matches.get(next_num)
            bracket_pairs.append({"left": left, "right": right})

    return templates.TemplateResponse("matches.html", {
        "request": request, "user": user,
        "matches": match_list, "phases": PHASES,
        "current_phase": phase, "is_grupos": phase == "Grupos",
        "user_names": user_names,
        "today_matches": today_matches,
        "today": today,
        "bracket_pairs": bracket_pairs,
    })


@router.get("/admin/sync-results")
async def sync_results_get(request: Request, phase: str = "Grupos"):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    await _sync_results()
    return RedirectResponse(f"/matches?phase={phase}", status_code=302)


@router.get("/admin/api-check")
async def api_check(request: Request):
    from fastapi.responses import JSONResponse
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    api_key = os.environ.get("FOOTBALL_API_KEY", "")
    async with httpx.AsyncClient(timeout=10) as client:
        r2 = await client.get("https://api.football-data.org/v4/competitions/WC/matches",
                              headers={"X-Auth-Token": api_key})
        return JSONResponse({"status": r2.status_code, "preview": r2.text[:800]})


async def _sync_results():
    api_key = os.environ.get("FOOTBALL_API_KEY", "")
    if not api_key:
        return

    # Get existing results to skip already processed matches
    existing = {r["match_numero"] for r in query("SELECT match_numero FROM results")}

    from datetime import timedelta
    import pytz
    now_utc = datetime.utcnow()
    yesterday_utc = (now_utc - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_utc = (now_utc + timedelta(days=1)).strftime("%Y-%m-%d")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://api.football-data.org/v4/competitions/WC/matches?dateFrom={yesterday_utc}&dateTo={tomorrow_utc}",
            headers={"X-Auth-Token": api_key}
        )
        if resp.status_code != 200:
            return
        data = resp.json()
        for m in data.get("matches", []):
            if m["status"] != "FINISHED":
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
            else:
                existing = query(
                    "SELECT match_numero FROM results WHERE local = %s AND visitante = %s",
                    (home, away)
                )
                if existing:
                    match_num = existing[0]["match_numero"]
                    
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
                INSERT INTO results (match_numero, fase, local, visitante, goles_local, goles_visitante,
                     avanza, pts_local, pts_visitante)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (match_numero) DO UPDATE SET
                    local=EXCLUDED.local, visitante=EXCLUDED.visitante,
                    goles_local=EXCLUDED.goles_local, goles_visitante=EXCLUDED.goles_visitante,
                    avanza=EXCLUDED.avanza, pts_local=EXCLUDED.pts_local,
                    pts_visitante=EXCLUDED.pts_visitante
            """, (match_num, fase, home, away, gl, gv, avanza, pts_local, pts_visitante))

            # Update bonus for all pronosticos of this match
            if finished and gl is not None and gv is not None:
                from routers.pronosticos import calc_bonus
                pros = query("SELECT * FROM pronosticos WHERE match_numero = %s", (match_num,))
                for p in pros:
                    bonus = calc_bonus(p["goles_local"], p["goles_visitante"], gl, gv)
                    if bonus is not None:
                        execute("UPDATE pronosticos SET puntos_bonus = %s WHERE id = %s",
                               (bonus, p["id"]))


@router.get("/debug/pronostico/{match_num}")
async def debug_pronostico(request: Request, match_num: int):
    from fastapi.responses import JSONResponse
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "not logged in"})
    
    # Get all pronosticos
    all_pros = query("SELECT * FROM pronosticos")
    match_pros = [p for p in all_pros if p["match_numero"] == match_num]
    my_pros = [p for p in all_pros if p["username"] == user["username"]]
    
    return JSONResponse({
        "user": user["username"],
        "match_num": match_num,
        "match_num_type": str(type(match_num)),
        "all_pros_count": len(all_pros),
        "match_pros": match_pros,
        "my_pros_all_matches": my_pros,
        "pros_by_match_keys": list(set(p["match_numero"] for p in all_pros)),
    })
