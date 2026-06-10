from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_admin_client
from auth import get_current_user, require_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")

BOMBOS = {
    "A": {"pts_victoria": 1.0,  "pts_empate": 0.5},
    "B": {"pts_victoria": 1.5,  "pts_empate": 0.75},
    "C": {"pts_victoria": 2.0,  "pts_empate": 1.0},
    "D": {"pts_victoria": 3.0,  "pts_empate": 1.5},
}


def get_bombo(ranking: int) -> str:
    if ranking <= 12: return "A"
    if ranking <= 24: return "B"
    if ranking <= 36: return "C"
    return "D"


@router.get("/draft", response_class=HTMLResponse)
async def draft_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    sb = get_admin_client()
    teams = sb.table("teams").select("*").order("ranking_compuesto").execute().data
    picks = sb.table("picks").select("*, profiles(nombre), teams(nombre, bombo)").order("pick_numero").execute().data
    profiles = sb.table("profiles").select("*").order("draft_orden").execute().data
    profile = sb.table("profiles").select("*").eq("id", user.id).single().execute().data

    # Teams already picked
    picked_team_ids = {p["team_id"] for p in picks}

    # Current pick number
    current_pick = len(picks) + 1
    current_participant = None
    if current_pick <= 48 and profiles:
        # Snake draft order
        snake = _snake_order(profiles)
        if current_pick <= len(snake):
            current_participant = snake[current_pick - 1]

    return templates.TemplateResponse("draft.html", {
        "request": request,
        "user": user,
        "profile": profile,
        "teams": teams,
        "picks": picks,
        "picked_team_ids": picked_team_ids,
        "profiles": profiles,
        "current_pick": current_pick,
        "current_participant": current_participant,
        "bombos": BOMBOS,
    })


def _snake_order(profiles):
    sorted_profiles = sorted(profiles, key=lambda p: p.get("draft_orden") or 99)
    order = []
    for ronda in range(4):
        if ronda % 2 == 0:
            order.extend(sorted_profiles)
        else:
            order.extend(reversed(sorted_profiles))
    return order


@router.post("/draft/pick")
async def make_pick(request: Request, team_id: str = Form(...)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    sb = get_admin_client()

    # Validate it's this user's turn
    picks = sb.table("picks").select("*").order("pick_numero").execute().data
    profiles = sb.table("profiles").select("*").order("draft_orden").execute().data
    profile = sb.table("profiles").select("*").eq("id", user.id).single().execute().data

    current_pick = len(picks) + 1
    if current_pick > 48:
        raise HTTPException(status_code=400, detail="El draft ya terminó")

    snake = _snake_order(profiles)
    current_participant = snake[current_pick - 1]

    if current_participant["id"] != str(user.id):
        raise HTTPException(status_code=403, detail="No es tu turno")

    # Validate team not taken
    taken = {p["team_id"] for p in picks}
    if team_id in taken:
        raise HTTPException(status_code=400, detail="Equipo ya elegido")

    # Validate no same group conflict (unless exception)
    team = sb.table("teams").select("*").eq("id", team_id).single().execute().data
    my_picks = [p for p in picks if p["participant_id"] == str(user.id)]
    my_team_ids = [p["team_id"] for p in my_picks]
    my_teams = sb.table("teams").select("*").in_("id", my_team_ids).execute().data if my_team_ids else []
    group_conflict = any(t["grupo_oficial"] and t["grupo_oficial"] == team.get("grupo_oficial") for t in my_teams)

    ronda = ((current_pick - 1) // 12) + 1

    sb.table("picks").insert({
        "pick_numero": current_pick,
        "ronda": ronda,
        "participant_id": str(user.id),
        "team_id": team_id,
        "group_conflict": group_conflict,
        "exception_authorized": False,
    }).execute()

    return RedirectResponse("/draft", status_code=302)


@router.post("/draft/exception/{pick_id}")
async def authorize_exception(request: Request, pick_id: str):
    require_admin(request)
    sb = get_admin_client()
    sb.table("picks").update({"exception_authorized": True}).eq("id", pick_id).execute()
    return RedirectResponse("/draft", status_code=302)


@router.get("/admin/draft-order", response_class=HTMLResponse)
async def draft_order_page(request: Request):
    require_admin(request)
    sb = get_admin_client()
    profiles = sb.table("profiles").select("*").order("nombre").execute().data
    return templates.TemplateResponse("admin_draft_order.html", {
        "request": request,
        "profiles": profiles,
    })


@router.post("/admin/draft-order")
async def save_draft_order(request: Request):
    require_admin(request)
    form = await request.form()
    sb = get_admin_client()
    for key, val in form.items():
        if key.startswith("order_"):
            profile_id = key.replace("order_", "")
            sb.table("profiles").update({"draft_orden": int(val)}).eq("id", profile_id).execute()
    return RedirectResponse("/draft", status_code=302)
