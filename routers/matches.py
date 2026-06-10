from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_admin_client
from auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PHASES = ["Grupos", "Ronda de 32", "Octavos", "Cuartos", "Semifinal", "Tercer lugar", "Final"]


@router.get("/matches", response_class=HTMLResponse)
async def matches_page(request: Request, phase: str = "Grupos"):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    sb = get_admin_client()
    matches = sb.table("matches").select("*").eq("fase", phase).order("fecha").order("numero").execute().data
    teams = sb.table("teams").select("id, nombre").order("nombre").execute().data

    return templates.TemplateResponse("matches.html", {
        "request": request,
        "user": user,
        "matches": matches,
        "teams": teams,
        "phases": PHASES,
        "current_phase": phase,
    })


@router.post("/matches/{match_id}/result")
async def save_result(
    request: Request,
    match_id: str,
    goles_local: int = Form(...),
    goles_visitante: int = Form(...),
    equipo_avanza_id: str = Form(None),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    sb = get_admin_client()
    match = sb.table("matches").select("*").eq("id", match_id).single().execute().data

    update_data = {
        "goles_local": goles_local,
        "goles_visitante": goles_visitante,
        "estado": "Finalizado",
    }

    if match["fase"] != "Grupos" and equipo_avanza_id:
        update_data["equipo_avanza_id"] = equipo_avanza_id
        team = sb.table("teams").select("nombre").eq("id", equipo_avanza_id).single().execute().data
        update_data["equipo_avanza_nombre"] = team["nombre"] if team else None

    sb.table("matches").update(update_data).eq("id", match_id).execute()
    _recalculate_match_points(sb, match_id)

    return RedirectResponse(f"/matches?phase={match['fase']}", status_code=302)


def _recalculate_match_points(sb, match_id):
    match = sb.table("matches").select("*").eq("id", match_id).single().execute().data
    if match["estado"] != "Finalizado":
        return

    local_id = match["local_id"]
    visitante_id = match["visitante_id"]
    gl = match.get("goles_local") or 0
    gv = match.get("goles_visitante") or 0
    fase = match["fase"]
    avanza_id = match.get("equipo_avanza_id")

    local_team = sb.table("teams").select("pts_victoria,pts_empate").eq("id", local_id).single().execute().data if local_id else None
    visitante_team = sb.table("teams").select("pts_victoria,pts_empate").eq("id", visitante_id).single().execute().data if visitante_id else None

    pts_local = 0.0
    pts_visitante = 0.0

    if fase == "Grupos" and local_team and visitante_team:
        if gl > gv:
            pts_local = float(local_team["pts_victoria"])
        elif gl == gv:
            pts_local = float(local_team["pts_empate"])
            pts_visitante = float(visitante_team["pts_empate"])
        else:
            pts_visitante = float(visitante_team["pts_victoria"])
    else:
        if avanza_id == local_id and local_team:
            pts_local = float(local_team["pts_victoria"])
        elif avanza_id == visitante_id and visitante_team:
            pts_visitante = float(visitante_team["pts_victoria"])

    sb.table("matches").update({
        "pts_local": pts_local,
        "pts_visitante": pts_visitante,
    }).eq("id", match_id).execute()
