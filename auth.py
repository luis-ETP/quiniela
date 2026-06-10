from fastapi import Request, HTTPException
from data import USERS

def get_current_user(request: Request):
    username = request.session.get("username")
    if not username or username not in USERS:
        return None
    return {"username": username, **USERS[username]}

def require_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)
    return user

def require_admin(request: Request):
    user = require_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403)
    return user
