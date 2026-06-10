from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user
from database import query, execute
from data import MATCHES_BY_NUM, TEAMS
from flags import normalize, flag_url
import httpx, os

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PHASES = ["Grupos","Ronda de 32","Octavos","Cuartos","Semifinal","Tercer lugar","Final"]

STAGE_MAP = {
    "GROUP_STAGE": "Grupos",
    "ROUND_OF_32": "Ronda de 32",
    "ROUND_OF_16": "Octavos",
    "QUARTER_FINALS": "Cuartos",
    "SEMI_FINALS": "Semifinal",
    "THIRD_PLACE": "Tercer lugar",
    "FINAL": "Final",
}


@router.get("/matches", response_class=HTMLResponse)
async def matches_page(request: Request, phase: str = "Grupos"):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Auto-sync on page load (non-blocking)
    try:
        await _sync_results()
    except Exception:
        pass

    results = query("SELECT * FROM results ORDER BY match_numero")
    results_by_num = {r["match_numero"]: r for r in results}

    if phase == "Grupos":
        match_list = []
        for m in sorted(MATCHES_BY_NUM.values(), key=lambda x: (x["fecha"], x["numero"])):
            if m["fase"] != "Grupos":
                continue
            mc = m.copy()
            mc["resultado"] = results_by_num.get(m["numero"])
            mc["flag_local"] = flag_url(m["local"])
            mc["flag_visitante"] = flag_url(m["visitante"])
            match_list.append(mc)
    else:
        # Knockout: get from results table
        match_list = []
        ko_results = [r for r in results if r.get("fase") == phase]
        ko_results.sort(key=lambda x: x["match_numero"])
        for r in ko_results:
            match_list.append({
                "numero": r["match_numero"],
                "fecha": str(r.get("fecha", "")),
                "fase": phase,
                "grupo": "",
                "local": r.get("local", "TBD"),
                "visitante": r.get("visitante", "TBD"),
                "flag_local": flag(r.get("local", "")),
                "flag_visitante": flag(r.get("visitante", "")),
                "resultado": r,
            })

    return templates.TemplateResponse("matches.html", {
        "request": request,
        "user": user,
        "matches": match_list,
        "phases": PHASES,
        "current_phase": phase,
        "is_grupos": phase == "Grupos",
    })


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
        # Check available competitions
        r1 = await client.get(
            "https://api.football-data.org/v4/competitions",
            headers={"X-Auth-Token": api_key},
        )
        # Check WC matches
        r2 = await client.get(
            "https://api.football-data.org/v4/competitions/WC/matches",
            headers={"X-Auth-Token": api_key},
        )
        return JSONResponse({
            "competitions_status": r1.status_code,
            "wc_matches_status": r2.status_code,
            "wc_response_preview": r2.text[:500],
        })
