import os
from fastapi import Request, HTTPException

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

USERS = {
    "messi10":       {"password": "Copa#737",     "nombre": "Messi10"},
    "ronaldo7":      {"password": "Gol#291",      "nombre": "Ronaldo7"},
    "mbappe9":       {"password": "Draft#445",    "nombre": "Mbappe9"},
    "neymar11":      {"password": "Bombo#183",    "nombre": "Neymar11"},
    "haaland9":      {"password": "Mundial#562",  "nombre": "Haaland9"},
    "vinicius7":     {"password": "Crack#819",    "nombre": "Vinicius7"},
    "bellingham8":   {"password": "Copa#374",     "nombre": "Bellingham8"},
    "pedri6":        {"password": "Gol#156",      "nombre": "Pedri6"},
    "salah11":       {"password": "Draft#923",    "nombre": "Salah11"},
    "ochoa":         {"password": "Bombo#647",    "nombre": "Ochoa"},
    "modric10":      {"password": "Mundial#381",  "nombre": "Modric10"},
    "debruyne17":    {"password": "Crack#294",    "nombre": "DeBruyne17"},
    "admin":         {"password": "Admin#2026!",  "nombre": "Admin", "is_admin": True},
}

def get_current_user(request: Request):
    username = request.session.get("username")
    if not username or username not in USERS:
        return None
    return {"username": username, **USERS[username]}

def require_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user

def require_admin(request: Request):
    user = require_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador")
    return user
