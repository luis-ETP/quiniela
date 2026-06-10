from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_client, get_admin_client
from auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        sb = get_client()
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        request.session["access_token"] = res.session.access_token
        request.session["user_id"] = str(res.user.id)
        return RedirectResponse("/", status_code=302)
    except Exception as e:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Correo o contraseña incorrectos"
        })


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    nombre: str = Form(...)
):
    try:
        sb = get_admin_client()
        res = sb.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"nombre": nombre}
        })
        # Create profile
        sb.table("profiles").insert({
            "id": str(res.user.id),
            "nombre": nombre,
            "email": email,
            "is_admin": False,
            "pagado": False
        }).execute()
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": None,
            "success": "Cuenta creada. Ya puedes iniciar sesión."
        })
    except Exception as e:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": str(e)
        })


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)
