from re import S
from fastapi import Request, Form
from starlette.status import HTTP_302_FOUND, HTTP_400_BAD_REQUEST
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.models import SessionDep, get_user, get_user_by_id, register_user, update_user
from app.core.config import templates, AUTH_QRCODE_ROOT_DIR
from app.models.users import User

from . import webApp, get_2FA_uri, verify2FAcode, login_required
from .forms import loginForm, registerForm, twoFactorAuthForm

from passlib.hash import pbkdf2_sha256 as secure_password
from pyotp import random_base32
from typing import Annotated
from os.path import join
from qrcode import make
from uuid import uuid4



# Root Route
@webApp.get("/", response_class=HTMLResponse)
async def root(req: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": req}
    )


# Home Route
@webApp.get("/home", response_class=HTMLResponse)
async def home(req: Request):
    return templates.TemplateResponse(
        "home.html",
        {"request": req}
    )

# Login Route
@webApp.post("/login/")
async def login(req: Request, data: Annotated[loginForm, Form()], session: SessionDep):
    user = get_user(data.email, session)
    if user is None:
        return templates.TemplateResponse(
            "home.html",
            {
                "request": req,
                "error": "Invalid email"
            }
        )

    if not secure_password.verify(data.password, user.password):
        return templates.TemplateResponse(
            "home.html",
            {
                "request": req,
                "error": "Invalid email or password"
            }
        )

    if verify2FAcode(user.uid, str(data.twoFA), session) is not True:
        return templates.TemplateResponse(
            "home.html",
            {
                "request": req,
                "error": "Invalid 2FA code"
            }
        )

    req.session[user.uid] = data.email
    return RedirectResponse("/web/test", status_code=HTTP_302_FOUND)

# Register Route
@webApp.post("/register/")
async def register(req: Request, data: Annotated[registerForm, Form()], session: SessionDep):
    user = User(
        uid=str(uuid4()),
        email=data.email,
        username=data.username,
        password=secure_password.hash(data.password),
        twoFA_secret=random_base32(),
    )

    status, msg = register_user(user, session)
    if status == 200:
        return RedirectResponse(f"/web/setup-2FA/{user.uid}", status_code=HTTP_302_FOUND)

    elif status == 500:
        return templates.TemplateResponse(
            "home.html",
            {
                "request": req,
                "error": msg
            }
        )


# 2FA Setup Route
@webApp.get('/setup-2FA/{uid}', response_class=HTMLResponse)
async def setup_2FA(req: Request, uid: str, session: SessionDep):
    user = get_user_by_id(uid, session)
    if user is not None:
        qr_uri = get_2FA_uri(user)
        twoFA_qr_img = make(str(qr_uri))

        qr_path = join(AUTH_QRCODE_ROOT_DIR, f'{user.uid}.png')
        twoFA_qr_img.save(qr_path)

        user.qr_code_path = qr_path
        update_user(user, session)

        return templates.TemplateResponse(
            "2FA-setup.html",
            {
                "request": req,
                "user": user,
            }
        )

@webApp.post('/setup-2FA/{uid}')
def verify2FA(req: Request, uid: str, data: Annotated[twoFactorAuthForm, Form()], session: SessionDep):
    code = data.verification_code
    user = get_user_by_id(uid, session)
    if user is not None:
        if verify2FAcode(uid, code, session):
            req.session[user.uid] = user.email
            return JSONResponse({
                'success': True,
                'message': '2FA enabled successfully',
            })

        return JSONResponse({
            'success': False,
            'message': 'Invalid verification code',
        }, status_code=HTTP_400_BAD_REQUEST)


# Logout Route
@webApp.get("/logout/")
@login_required()
async def logout(req: Request, session: SessionDep, current_user_uid: str = None):
    req.session.pop(current_user_uid)
    return RedirectResponse("/web/home", status_code=HTTP_302_FOUND)
