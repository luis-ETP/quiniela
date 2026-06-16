from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from auth import get_current_user
from database import query, execute
from data import KICKOFF_CDMX, USERS
from datetime import datetime
import pytz

router = APIRouter()
CDMX = pytz.timezone("America/Mexico_City")


def is_locked(match_num):
    ks = KICKOFF_CDMX.get(match_num)
    if not ks:
        return False
    return datetime.now(CDMX) >= CDMX.localize(datetime.fromisoformat(ks))


def calc_bonus(p_local, p_visit, r_local, r_visit):
    """Calculate bonus points for a pronostico."""
    if r_local is None or r_visit is None:
        return None  # Match not finished

    # Exact score
    if p_local == r_local and p_visit == r_visit:
        return 1.0

    # Draw - both predicted draw and it was a draw (but wrong score)
    if p_local == p_visit and r_local == r_visit:
        return 0.5

    # Correct goal difference
    p_diff = p_local - p_visit
    r_diff = r_local - r_visit
    if p_diff == r_diff:
        return 0.5

    # Correct winner (but wrong diff)
    p_winner = "local" if p_local > p_visit else ("visitante" if p_visit > p_local else "draw")
    r_winner = "local" if r_local > r_visit else ("visitante" if r_visit > r_local else "draw")

    if p_winner == r_winner:
        return 0.25

    # Wrong winner
    return -0.25


@router.post("/pronostico/{match_num}")
async def save_pronostico(
    request: Request,
    match_num: int,
    goles_local: int = Form(...),
    goles_visitante: int = Form(...),
):
    user = get_current_user(request)
    if not user or is_locked(match_num):
        return RedirectResponse("/matches", status_code=302)

    execute("""
        INSERT INTO pronosticos (match_numero, username, goles_local, goles_visitante)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (match_numero, username) DO UPDATE SET
            goles_local = EXCLUDED.goles_local,
            goles_visitante = EXCLUDED.goles_visitante
    """, (match_num, user["username"], goles_local, goles_visitante))

    return RedirectResponse("/matches", status_code=302)


def get_pronosticos_for_match(match_num, result=None):
    """Get all pronosticos for a match with bonus calculated."""
    pros = query("SELECT * FROM pronosticos WHERE match_numero = %s ORDER BY username", (match_num,))
    if result and result.get("goles_local") is not None:
        r_local = result["goles_local"]
        r_visit = result["goles_visitante"]
        for p in pros:
            bonus = calc_bonus(p["goles_local"], p["goles_visitante"], r_local, r_visit)
            p["puntos_bonus"] = bonus
            # Update in DB if not already set
            if bonus is not None and p.get("puntos_bonus") != bonus:
                execute("UPDATE pronosticos SET puntos_bonus = %s WHERE id = %s",
                       (bonus, p["id"]))
    return pros


def get_total_bonus_by_user():
    """Sum of bonus points per user across all matches."""
    rows = query("""
        SELECT username, COALESCE(SUM(puntos_bonus), 0) as total_bonus
        FROM pronosticos
        WHERE puntos_bonus IS NOT NULL
        GROUP BY username
    """)
    return {r["username"]: float(r["total_bonus"]) for r in rows}
