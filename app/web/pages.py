from fastapi import Request
from starlette.status import HTTP_302_FOUND
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.auth import get_qrcode, login_required
from app.core.sLogger import security_logger
from app.core.config import templates

from app.models import get_user_devices
from app.models import SessionDep, get_user_by_id

from . import webApp, get_2FA_uri

from typing import Union
from logging import getLogger



logger = getLogger(__name__)


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


# 2FA Setup Route
@webApp.get('/auth/setup-2FA/{uid}', response_class=HTMLResponse)
async def setup_2FA(req: Request, uid: str, session: SessionDep):
    user = get_user_by_id(uid, session)
    if user is not None:
        qr_uri = get_2FA_uri(user)
        stats, qr_code = get_qrcode(data=qr_uri)

        if stats != 200:
            return JSONResponse({
                'message': 'Unable to generate QR Code!'
            }, status_code=stats)

        return templates.TemplateResponse(
            "2FA-setup.html",
            {
                "request": req,
                "user": user,
                "qr_data": qr_code
            }
        )


# Forgot Password Route
@webApp.get("/account/security/forgot-password", response_class=HTMLResponse)
async def forgot_password(req: Request):
    return templates.TemplateResponse(
        "forgot-password.html",
        {"request": req}
    )


# Password Reset Route
@webApp.get("/account/security/password-reset/{uid}", response_class=HTMLResponse)
async def password_reset_form(req: Request, uid: str, session: SessionDep, code: Union[str, None] = None):
    user = get_user_by_id(uid, session)
    if user is None:
        return RedirectResponse(req.url_for('forgot_password'), status_code=HTTP_302_FOUND)

    return templates.TemplateResponse(
        "password-reset.html",
        {
            "request": req,
            "uid": user.uid,
            "code_hash": code
        }
    )


# Account Center Route
@webApp.get("/account/{uid}", response_class=HTMLResponse)
@login_required()
async def account_center(req: Request, session: SessionDep, current_user_uid: str|None=None):
    user = get_user_by_id(str(current_user_uid), session)
    return templates.TemplateResponse(
        "account-center.html",
        {
            "request": req,
            "user": user,
        }
    )


# Logout Route
@webApp.get("/account/logout/")
@login_required()
async def logout(req: Request, session: SessionDep, current_user_uid: str|None=None):
    client_ip = req.client.host if req.client else 'unknown'
    security_logger.info(f"User logged out: {current_user_uid} from IP: {client_ip}")

    req.session.pop(str(current_user_uid))
    return RedirectResponse(req.url_for('home'), status_code=HTTP_302_FOUND)


# Dashboard Route
@webApp.get("/dashboard/{uid}", response_class=HTMLResponse)
@login_required()
async def dashboard(req: Request, uid: str, session: SessionDep, current_user_uid: str|None=None):
    devices = get_user_devices(owner_uid=uid, session=session)
    user = get_user_by_id(uid, session)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": req,
            "devices": devices,
            "user": user,
        }
    )
