from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user, require_admin
from database import query, execute
from data import TEAMS, TEAMS_BY_RANKING, USERS
from flags import flag_url
import random

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PARTICIPANTS = [u for u, d in USERS.items() if not d.get("is_admin")]

def snake_order(draft_order):
    result = []
    for ronda in range(4):
        result.extend(draft_order if ronda % 2 == 0 else list(reversed(draft_order)))
    return result

def get_draft_state():
    picks = query("SELECT * FROM picks ORDER BY pick_numero")
    cfg = query("SELECT * FROM draft_config ORDER BY orden")
    draft_order = [d["username"] for d in cfg]
    picked_teams = {p["team_nombre"] for p in picks}
    current_pick = len(picks) + 1
    current_participant = None
    ronda_actual = None
    if current_pick <= 48 and draft_order:
        snake = snake_order(draft_order)
        current_participant = snake[current_pick - 1]
        ronda_actual = ((current_pick - 1) // 12) + 1
    return picks, draft_order, picked_teams, current_pick, current_participant, ronda_actual


@router.get("/draft", response_class=HTMLResponse)
async def draft_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    picks, draft_order, picked_teams, current_pick, current_participant, ronda_actual = get_draft_state()
    is_my_turn = current_participant == user["username"]
    draft_configured = len(draft_order) == 12
    draft_done = current_pick > 48

    # Build teams with flags, sorted by bombo then ranking
    available_teams = []
    for t in TEAMS_BY_RANKING:
        available_teams.append({
            **t,
            "flag_url": flag_url(t["nombre"]),
            "taken": t["nombre"] in picked_teams,
        })

    # Build pick history with participant names
    picks_display = []
    for p in picks:
        picks_display.append({
            **p,
            "nombre": USERS.get(p["participant_username"], {}).get("nombre", p["participant_username"]),
            "flag_url": flag_url(p["team_nombre"]),
        })

    # My picks
    my_picks = [p for p in picks if p["participant_username"] == user["username"]]
    my_teams_by_bombo = {}
    for p in my_picks:
        my_teams_by_bombo[p["bombo"]] = p["team_nombre"]

    # Draft order display
    order_display = []
    for i, uname in enumerate(draft_order):
        order_display.append({
            "orden": i + 1,
            "username": uname,
            "nombre": USERS.get(uname, {}).get("nombre", uname),
            "is_current": uname == user["username"],
        })

    return templates.TemplateResponse("draft.html", {
        "request": request,
        "user": user,
        "teams": available_teams,
        "picks": picks_display,
        "picked_teams": picked_teams,
        "current_pick": current_pick,
        "current_participant": current_participant,
        "current_participant_nombre": USERS.get(current_participant, {}).get("nombre", current_participant) if current_participant else None,
        "ronda_actual": ronda_actual,
        "is_my_turn": is_my_turn,
        "draft_configured": draft_configured,
        "draft_done": draft_done,
        "my_teams_by_bombo": my_teams_by_bombo,
        "order_display": order_display,
        "total_picks": len(picks),
    })


@router.post("/draft/pick")
async def make_pick(request: Request, team_nombre: str = Form(...)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    picks, draft_order, picked_teams, current_pick, current_participant, ronda_actual = get_draft_state()

    if current_pick > 48:
        raise HTTPException(status_code=400, detail="Draft terminado")
    if current_participant != user["username"]:
        raise HTTPException(status_code=403, detail="No es tu turno")
    if team_nombre in picked_teams:
        raise HTTPException(status_code=400, detail="Equipo ya elegido")

    team = TEAMS.get(team_nombre)
    if not team:
        raise HTTPException(status_code=400, detail="Equipo inválido")

    my_teams = [TEAMS[p["team_nombre"]] for p in picks
                if p["participant_username"] == user["username"] and TEAMS.get(p["team_nombre"])]
    group_conflict = any(t["grupo"] == team["grupo"] for t in my_teams)

    execute("""
        INSERT INTO picks (pick_numero, ronda, participant_username, team_nombre, bombo, group_conflict, exception_authorized)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (current_pick, ronda_actual, user["username"], team_nombre, team["bombo"], group_conflict, False))

    return RedirectResponse("/draft", status_code=302)


@router.post("/draft/exception/{pick_id}")
async def authorize_exception(request: Request, pick_id: str):
    require_admin(request)
    execute("UPDATE picks SET exception_authorized = true WHERE id = %s", (pick_id,))
    return RedirectResponse("/draft", status_code=302)


@router.post("/draft/undo")
async def undo_last_pick(request: Request):
    require_admin(request)
    last = query("SELECT * FROM picks ORDER BY pick_numero DESC LIMIT 1")
    if last:
        execute("DELETE FROM picks WHERE id = %s", (last[0]["id"],))
    return RedirectResponse("/draft", status_code=302)


# ── Admin: sorteo y orden ─────────────────────────────────────────────────────

@router.get("/admin/draft-order", response_class=HTMLResponse)
async def draft_order_page(request: Request):
    require_admin(request)
    cfg = query("SELECT * FROM draft_config ORDER BY orden")
    existing_order = [d["username"] for d in cfg]
    return templates.TemplateResponse("admin_draft_order.html", {
        "request": request,
        "user": get_current_user(request),
        "existing_order": existing_order,
        "all_users": PARTICIPANTS,
        "user_names": {u: USERS[u]["nombre"] for u in PARTICIPANTS},
        "draft_configured": len(existing_order) == 12,
    })


@router.post("/admin/draft-sorteo")
async def sorteo(request: Request):
    require_admin(request)
    shuffled = PARTICIPANTS.copy()
    random.shuffle(shuffled)
    execute("DELETE FROM draft_config")
    for i, uname in enumerate(shuffled):
        execute("INSERT INTO draft_config (username, orden) VALUES (%s, %s)", (uname, i + 1))
    return RedirectResponse("/admin/draft-order", status_code=302)


@router.post("/admin/draft-order")
async def save_draft_order(request: Request):
    require_admin(request)
    form = await request.form()
    execute("DELETE FROM draft_config")
    for i in range(1, 13):
        uname = form.get(f"pos_{i}")
        if uname:
            execute("INSERT INTO draft_config (username, orden) VALUES (%s, %s)", (uname, i))
    return RedirectResponse("/admin/draft-order", status_code=302)


@router.post("/admin/draft-reset")
async def reset_draft(request: Request):
    require_admin(request)
    execute("DELETE FROM picks")
    return RedirectResponse("/draft", status_code=302)
