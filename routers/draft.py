from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user, require_admin
from database import query, execute
from data import TEAMS, TEAMS_BY_RANKING, USERS
from flags import flag_url
from datetime import datetime, timezone

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PARTICIPANTS = [u for u, d in USERS.items() if not d.get("is_admin")]
TIMEOUT_SECONDS = 60


def snake_order(draft_order):
    result = []
    for ronda in range(4):
        result.extend(draft_order if ronda % 2 == 0 else list(reversed(draft_order)))
    return result


def get_draft_state():
    picks = query("SELECT * FROM picks ORDER BY pick_numero")
    cfg = query("SELECT * FROM draft_config ORDER BY orden")
    state = query("SELECT * FROM draft_state WHERE id = 1")
    draft_order = [d["username"] for d in cfg]
    picked_teams = {p["team_nombre"] for p in picks}
    current_pick = len(picks) + 1
    current_participant = None
    ronda_actual = None
    if current_pick <= 48 and draft_order:
        snake = snake_order(draft_order)
        current_participant = snake[current_pick - 1]
        ronda_actual = ((current_pick - 1) // 12) + 1
    started = state[0]["started"] if state else False
    pick_started_at = state[0]["current_pick_started_at"] if state else None
    return picks, draft_order, picked_teams, current_pick, current_participant, ronda_actual, started, pick_started_at


def auto_pick(picked_teams, participant_username):
    """Pick best available team by ranking, avoiding group conflicts."""
    my_picks = query("SELECT * FROM picks WHERE participant_username = %s", (participant_username,))
    my_groups = {TEAMS[p["team_nombre"]]["grupo"] for p in my_picks if TEAMS.get(p["team_nombre"])}

    for team in TEAMS_BY_RANKING:
        if team["nombre"] in picked_teams:
            continue
        # Try to avoid group conflict
        if team["grupo"] not in my_groups:
            return team
    # If all have conflicts, just pick best available
    for team in TEAMS_BY_RANKING:
        if team["nombre"] not in picked_teams:
            return team
    return None


def do_pick(current_pick, ronda_actual, participant_username, team):
    my_picks = query("SELECT * FROM picks WHERE participant_username = %s", (participant_username,))
    my_teams = [TEAMS[p["team_nombre"]] for p in my_picks if TEAMS.get(p["team_nombre"])]
    group_conflict = any(t["grupo"] == team["grupo"] for t in my_teams)
    execute("""
        INSERT INTO picks (pick_numero, ronda, participant_username, team_nombre, bombo, group_conflict, exception_authorized)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (current_pick, ronda_actual, participant_username, team["nombre"], team["bombo"], group_conflict, False))
    # Reset pick timer
    execute("UPDATE draft_state SET current_pick_started_at = %s WHERE id = 1",
            (datetime.now(timezone.utc),))


def check_and_auto_pick(picks, draft_order, picked_teams, current_pick, current_participant, ronda_actual, pick_started_at):
    """Auto-pick if timeout expired. Returns True if auto-pick happened."""
    if not pick_started_at or not current_participant or current_pick > 48:
        return False
    if isinstance(pick_started_at, str):
        pick_started_at = datetime.fromisoformat(pick_started_at)
    now = datetime.now(timezone.utc)
    if pick_started_at.tzinfo is None:
        pick_started_at = pick_started_at.replace(tzinfo=timezone.utc)
    elapsed = (now - pick_started_at).total_seconds()
    if elapsed >= TIMEOUT_SECONDS:
        team = auto_pick(picked_teams, current_participant)
        if team:
            do_pick(current_pick, ronda_actual, current_participant, team)
            return True
    return False


@router.get("/draft", response_class=HTMLResponse)
async def draft_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    picks, draft_order, picked_teams, current_pick, current_participant, ronda_actual, started, pick_started_at = get_draft_state()

    # Check auto-pick timeout
    if started and current_pick <= 48:
        if check_and_auto_pick(picks, draft_order, picked_teams, current_pick, current_participant, ronda_actual, pick_started_at):
            return RedirectResponse("/draft", status_code=302)

    is_my_turn = started and current_participant == user["username"]
    draft_configured = len(draft_order) == 12
    draft_done = current_pick > 48

    # Seconds remaining for timer
    seconds_remaining = None
    if started and pick_started_at and current_pick <= 48:
        if isinstance(pick_started_at, str):
            pick_started_at = datetime.fromisoformat(pick_started_at)
        now = datetime.now(timezone.utc)
        if pick_started_at.tzinfo is None:
            pick_started_at = pick_started_at.replace(tzinfo=timezone.utc)
        elapsed = (now - pick_started_at).total_seconds()
        seconds_remaining = max(0, TIMEOUT_SECONDS - int(elapsed))

    available_teams = []
    for t in TEAMS_BY_RANKING:
        available_teams.append({
            **t,
            "flag_url": flag_url(t["nombre"]),
            "taken": t["nombre"] in picked_teams,
        })

    picks_display = []
    for p in reversed(picks):
        picks_display.append({
            **p,
            "nombre": USERS.get(p["participant_username"], {}).get("nombre", p["participant_username"]),
            "flag_url": flag_url(p["team_nombre"]),
        })

    my_picks = [p for p in picks if p["participant_username"] == user["username"]]
    my_teams_by_bombo = {p["bombo"]: p["team_nombre"] for p in my_picks}

    order_display = [{"orden": i+1, "username": u, "nombre": USERS.get(u, {}).get("nombre", u),
                      "is_current": u == current_participant}
                     for i, u in enumerate(draft_order)]

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
        "draft_started": started,
        "my_teams_by_bombo": my_teams_by_bombo,
        "order_display": order_display,
        "total_picks": len(picks),
        "seconds_remaining": seconds_remaining,
        "timeout": TIMEOUT_SECONDS,
    })


@router.post("/draft/pick")
async def make_pick(request: Request, team_nombre: str = Form(...)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    picks, draft_order, picked_teams, current_pick, current_participant, ronda_actual, started, pick_started_at = get_draft_state()

    if not started:
        raise HTTPException(status_code=400, detail="El draft no ha comenzado")
    if current_pick > 48:
        raise HTTPException(status_code=400, detail="Draft terminado")
    if current_participant != user["username"]:
        raise HTTPException(status_code=403, detail="No es tu turno")
    if team_nombre in picked_teams:
        raise HTTPException(status_code=400, detail="Equipo ya elegido")

    team = TEAMS.get(team_nombre)
    if not team:
        raise HTTPException(status_code=400, detail="Equipo inválido")

    do_pick(current_pick, ronda_actual, user["username"], team)
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
        execute("UPDATE draft_state SET current_pick_started_at = %s WHERE id = 1",
                (datetime.now(timezone.utc),))
    return RedirectResponse("/draft", status_code=302)


@router.post("/admin/draft-start")
async def start_draft(request: Request):
    require_admin(request)
    execute("UPDATE draft_state SET started = true, current_pick_started_at = %s WHERE id = 1",
            (datetime.now(timezone.utc),))
    return RedirectResponse("/draft", status_code=302)


@router.post("/admin/draft-reset")
async def reset_draft(request: Request):
    require_admin(request)
    execute("DELETE FROM picks")
    execute("UPDATE draft_state SET started = false, current_pick_started_at = NULL WHERE id = 1")
    return RedirectResponse("/draft", status_code=302)


@router.get("/admin/draft-order", response_class=HTMLResponse)
async def draft_order_page(request: Request):
    require_admin(request)
    cfg = query("SELECT * FROM draft_config ORDER BY orden")
    existing_order = [d["username"] for d in cfg]
    state = query("SELECT * FROM draft_state WHERE id = 1")
    draft_started = state[0]["started"] if state else False
    return templates.TemplateResponse("admin_draft_order.html", {
        "request": request,
        "user": get_current_user(request),
        "existing_order": existing_order,
        "all_users": PARTICIPANTS,
        "user_names": {u: USERS[u]["nombre"] for u in PARTICIPANTS},
        "draft_configured": len(existing_order) == 12,
        "draft_started": draft_started,
    })


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
