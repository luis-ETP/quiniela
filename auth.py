import os
from fastapi import Request, HTTPException
from database import get_admin_client

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

def get_current_user(request: Request):
    token = request.session.get("access_token")
    if not token:
        return None
    try:
        sb = get_admin_client()
        user = sb.auth.get_user(token)
        return user.user
    except Exception:
        return None

def require_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user

def require_admin(request: Request):
    user = require_user(request)
    sb = get_admin_client()
    profile = sb.table("profiles").select("is_admin").eq("id", user.id).single().execute()
    if not profile.data or not profile.data.get("is_admin"):
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador")
    return user
