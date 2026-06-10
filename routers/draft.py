from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user, require_admin
from database import get_db
from data import TEAMS, TEAMS_BY_RANKING, USERS

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def snake_order(draft_order):
    # draft_order: list of usernames in order 1..12
    result = []
    for ronda in range(4):
        result.extend(draft_order if ronda % 2 == 0 else list(reversed(draft_order)))
    return result

@router.get("/draft", response_class=HTMLResponse)
async def draft_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    db = get_db()
    picks = db.table("picks").select("*").order("pick_numero").execute().data
    draft_cfg = db.table("draft_config").select("*").order("orden").execute().data

    draft_order = [d["username"] for d in draft_cfg] if draft_cfg else []
    picked_teams = {p["team_nombre"] for p in picks}
    current_pick = len(picks) + 1
    current_participant = None
    if current_pick <= 48 and draft_order:
        snake = snake_order(draft_order)
        current_participant = snake[current_pick - 1]

    ronda_actual = ((current_pick - 1) // 12) + 1 if current_pick <= 48 else None

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

    db = get_db()
    picks = db.table("picks").select("*").order("pick_numero").execute().data
    draft_cfg = db.table("draft_config").select("*").order("orden").execute().data
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

    # Check group conflict
    my_teams = [TEAMS[p["team_nombre"]] for p in picks if p["participant_username"] == user["username"] and p["team_nombre"] in TEAMS]
    group_conflict = any(t["grupo"] == team["grupo"] for t in my_teams)

    ronda = ((current_pick - 1) // 12) + 1
    db.table("picks").insert({
        "pick_numero": current_pick,
        "ronda": ronda,
        "participant_username": user["username"],
        "team_nombre": team_nombre,
        "bombo": team["bombo"],
        "group_conflict": group_conflict,
        "exception_authorized": False,
    }).execute()

    return RedirectResponse("/draft", status_code=302)

@router.post("/draft/exception/{pick_id}")
async def authorize_exception(request: Request, pick_id: str):
    require_admin(request)
    get_db().table("picks").update({"exception_authorized": True}).eq("id", pick_id).execute()
    return RedirectResponse("/draft", status_code=302)

@router.get("/admin/draft-order", response_class=HTMLResponse)
async def draft_order_page(request: Request):
    require_admin(request)
    db = get_db()
    cfg = db.table("draft_config").select("*").order("orden").execute().data
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
    db = get_db()
    db.table("draft_config").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    rows = []
    for i in range(1, 13):
        uname = form.get(f"pos_{i}")
        if uname:
            rows.append({"username": uname, "orden": i})
    if rows:
        db.table("draft_config").insert(rows).execute()
    return RedirectResponse("/draft", status_code=302)
