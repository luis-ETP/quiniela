from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from database import query, execute
from data import TEAMS, USERS, KICKOFF_CDMX, MATCHES_BY_NUM
from flags import flag_url
from datetime import datetime
import pytz

router = APIRouter()
templates = Jinja2Templates(directory="templates")
CDMX = pytz.timezone("America/Mexico_City")


def is_locked(match_num):
    ks = KICKOFF_CDMX.get(match_num)
    if not ks:
        return False
    return datetime.now(CDMX) >= CDMX.localize(datetime.fromisoformat(ks))


@router.get("/mis-equipos", response_class=HTMLResponse)
async def mis_equipos(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    picks = query("SELECT * FROM picks WHERE participant_username = %s", (user["username"],))
    results = query("SELECT * FROM results")

    # Points per team
    pts_by_team = {}
    vic_by_team = {}
    emp_by_team = {}
    der_by_team = {}
    for r in results:
        gl = r.get("goles_local")
        gv = r.get("goles_visitante")
        if gl is None or gv is None:
            continue
        gl, gv = int(gl), int(gv)
        for team, side in [(r.get("local",""), "local"), (r.get("visitante",""), "visitante")]:
            if not team: continue
            pts_by_team.setdefault(team, 0.0)
            vic_by_team.setdefault(team, 0)
            emp_by_team.setdefault(team, 0)
            der_by_team.setdefault(team, 0)
            pts = float(r.get(f"pts_{side}") or 0)
            pts_by_team[team] += pts
            if r["fase"] == "Grupos":
                if side == "local":
                    if gl > gv: vic_by_team[team] += 1
                    elif gl == gv: emp_by_team[team] += 1
                    else: der_by_team[team] += 1
                else:
                    if gv > gl: vic_by_team[team] += 1
                    elif gv == gl: emp_by_team[team] += 1
                    else: der_by_team[team] += 1
            elif r.get("avanza") == side:
                vic_by_team[team] += 1
            elif r.get("avanza") and r.get("avanza") != side:
                der_by_team[team] += 1

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
            "derrotas": der_by_team.get(tname, 0),
        }

    pts_total = sum(t["pts"] for t in picks_by_bombo.values())
    pts_cd = sum(t["pts"] for b, t in picks_by_bombo.items() if b in ("C","D"))
    total_victorias = sum(t["victorias"] for t in picks_by_bombo.values())
    total_empates = sum(t["empates"] for t in picks_by_bombo.values())
    total_derrotas = sum(t["derrotas"] for t in picks_by_bombo.values())

    # Duelos — fetch all where user is owner
    duelos = query("""
        SELECT * FROM duelos 
        WHERE owner1_username = %s OR owner2_username = %s
        ORDER BY match_numero
    """, (user["username"], user["username"]))

    user_names = {u: d["nombre"] for u, d in USERS.items()}

    # Enrich duelos with match info and lock status
    duelos_display = []
    balance = 0.0
    for d in duelos:
        mn = d["match_numero"]
        match_info = MATCHES_BY_NUM.get(mn, {})
        local = d.get("team1","")
        visitante = d.get("team2","")
        locked = is_locked(mn)
        kickoff = KICKOFF_CDMX.get(mn, "")
        is_owner1 = d["owner1_username"] == user["username"]
        my_apuesta = d["apuesta1"] if is_owner1 else d["apuesta2"]
        opp_apuesta = d["apuesta2"] if is_owner1 else d["apuesta1"]
        opp_username = d["owner2_username"] if is_owner1 else d["owner1_username"]

        # Balance
        if d.get("ganador_username"):
            monto_en_juego = min(d["apuesta1"] or 0, d["apuesta2"] or 0) if (d["apuesta1"] and d["apuesta2"]) else 0
            if d["ganador_username"] == user["username"]:
                balance += monto_en_juego
            else:
                balance -= monto_en_juego

        duelos_display.append({
            **d,
            "match_info": match_info,
            "fecha": match_info.get("fecha", ""),
            "local": local,
            "visitante": visitante,
            "flag_local": flag_url(local),
            "flag_visitante": flag_url(visitante),
            "locked": locked,
            "kickoff": kickoff,
            "is_owner1": is_owner1,
            "my_apuesta": my_apuesta,
            "opp_apuesta": opp_apuesta,
            "opp_username": opp_username,
            "opp_nombre": user_names.get(opp_username, opp_username),
        })

    return templates.TemplateResponse("mis_equipos.html", {
        "request": request,
        "user": user,
        "picks": picks,
        "picks_by_bombo": picks_by_bombo,
        "pts_total": round(pts_total, 2),
        "pts_cd": round(pts_cd, 2),
        "total_victorias": total_victorias,
        "total_empates": total_empates,
        "total_derrotas": total_derrotas,
        "duelos": duelos_display,
        "balance": round(balance, 2),
        "user_names": user_names,
    })


@router.post("/duelo/{match_num}/apuesta")
async def set_apuesta(request: Request, match_num: int, monto: float = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    if is_locked(match_num):
        return RedirectResponse("/mis-equipos", status_code=302)
    if monto < 20 or monto > 100:
        return RedirectResponse("/mis-equipos", status_code=302)

    duelo = query("SELECT * FROM duelos WHERE match_numero = %s", (match_num,))
    if not duelo:
        return RedirectResponse("/mis-equipos", status_code=302)
    duelo = duelo[0]

    if user["username"] == duelo["owner1_username"]:
        execute("UPDATE duelos SET apuesta1 = %s WHERE match_numero = %s", (monto, match_num))
    elif user["username"] == duelo["owner2_username"]:
        execute("UPDATE duelos SET apuesta2 = %s WHERE match_numero = %s", (monto, match_num))

    return RedirectResponse("/mis-equipos", status_code=302)
