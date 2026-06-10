from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user, require_admin
from database import query, execute
from data import TEAMS, TEAMS_BY_RANKING, USERS

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def snake_order(draft_order):
    result = []
    for ronda in range(4):
        result.extend(draft_order if ronda % 2 == 0 else list(reversed(draft_order)))
    return result

@router.get("/draft", response_class=HTMLResponse)
async def draft_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    picks = query("SELECT * FROM picks ORDER BY pick_numero")
    draft_cfg = query("SELECT * FROM draft_config ORDER BY orden")
    draft_order = [d["username"] for d in draft_cfg]
    picked_teams = {p["team_nombre"] for p in picks}
    current_pick = len(picks) + 1
    current_participant = None
    ronda_actual = None

    if current_pick <= 48 and draft_order:
        snake = snake_order(draft_order)
        current_participant = snake[current_pick - 1]
        ronda_actual = ((current_pick - 1) // 12) + 1

    return templates.TemplateResponse("draft.html", {
        "request": request,
        "user": user,
        "teams": TEAMS_BY_RANKING,
        "picks": picks,
        "picked_teams": picked_teams,
        "current_pick": current_pick,
        "current_participant": current_participant,
        "ronda_actual": ronda_actual,
        "draft_order": draft_order,
    })

@router.post("/draft/pick")
async def make_pick(request: Request, team_nombre: str = Form(...)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    picks = query("SELECT * FROM picks ORDER BY pick_numero")
    draft_cfg = query("SELECT * FROM draft_config ORDER BY orden")
    draft_order = [d["username"] for d in draft_cfg]

    current_pick = len(picks) + 1
    if current_pick > 48:
        raise HTTPException(status_code=400, detail="Draft terminado")

    snake = snake_order(draft_order)
    if snake[current_pick - 1] != user["username"]:
        raise HTTPException(status_code=403, detail="No es tu turno")

    picked_teams = {p["team_nombre"] for p in picks}
    if team_nombre in picked_teams:
        raise HTTPException(status_code=400, detail="Equipo ya elegido")

    team = TEAMS.get(team_nombre)
    if not team:
        raise HTTPException(status_code=400, detail="Equipo inválido")

    my_teams = [TEAMS[p["team_nombre"]] for p in picks
                if p["participant_username"] == user["username"] and TEAMS.get(p["team_nombre"])]
    group_conflict = any(t["grupo"] == team["grupo"] for t in my_teams)
    ronda = ((current_pick - 1) // 12) + 1

    execute("""
        INSERT INTO picks (pick_numero, ronda, participant_username, team_nombre, bombo, group_conflict, exception_authorized)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (current_pick, ronda, user["username"], team_nombre, team["bombo"], group_conflict, False))

    return RedirectResponse("/draft", status_code=302)

@router.post("/draft/exception/{pick_id}")
async def authorize_exception(request: Request, pick_id: str):
    require_admin(request)
    execute("UPDATE picks SET exception_authorized = true WHERE id = %s", (pick_id,))
    return RedirectResponse("/draft", status_code=302)

@router.get("/admin/draft-order", response_class=HTMLResponse)
async def draft_order_page(request: Request):
    require_admin(request)
    cfg = query("SELECT * FROM draft_config ORDER BY orden")
    return templates.TemplateResponse("admin_draft_order.html", {
        "request": request,
        "user": get_current_user(request),
        "draft_cfg": cfg,
        "all_users": [u for u in USERS if not USERS[u].get("is_admin")],
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
    return RedirectResponse("/draft", status_code=302)
