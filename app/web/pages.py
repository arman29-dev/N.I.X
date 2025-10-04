from fastapi import Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.status import HTTP_302_FOUND, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.core.auth import get_qrcode, login_required, verify2FAcode
from app.core.config import templates, limiter
from app.core.sLogger import security_logger
from app.core.emailing import send_email

from app.models.users import User
from app.models import get_user_devices
from app.models import SessionDep, get_user_by_id, register_user, update_user

from . import webApp, get_2FA_uri
from .forms import registerForm, twoFactorAuthForm, passwordResetForm

from passlib.hash import pbkdf2_sha256 as secure_password
from typing import Annotated, Union
from pyotp import random_base32
from datetime import datetime
from logging import getLogger
from uuid import uuid4



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


# Register Route
@webApp.post("/auth/register/")
async def register(req: Request, data: Annotated[registerForm, Form()], session: SessionDep):
    client_ip = req.client.host if req.client else 'unknown'

    user = User(
        uid=str(uuid4()),
        email=data.email,
        username=data.username,
        password=secure_password.hash(data.password),
        twoFA_secret=random_base32(),
    )

    status, msg = register_user(user, session)
    if status == 200:
        security_logger.info(f"New user registered: {data.email} from IP: {client_ip}")
        return RedirectResponse(req.url_for('setup_2FA', uid=user.uid), status_code=HTTP_302_FOUND)

    elif status == 500:
        security_logger.error(f"Registration failed for {data.email}: {msg}",
            exc_info=True, extra={'client_ip': client_ip}
        )

        return templates.TemplateResponse(
            "home.html",
            {
                "request": req,
                "error": msg
            }
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

@webApp.post('/auth/setup-2FA/{uid}')
@limiter.limit("3/minute")
def verify2FA(request: Request, uid: str, data: Annotated[twoFactorAuthForm, Form()], session: SessionDep):
    code = data.verification_code
    user = get_user_by_id(uid, session)
    if user is not None:
        if verify2FAcode(uid, code, session):
            request.session[user.uid] = user.email

            email_template = templates.get_template("email/welcome.html")
            status, msg = send_email(
                to=user.email,
                subject="Welcome to N.I.X",
                body=email_template.render(user=user)
            )
            if status is not True:
                print(f"Email Sent Status: {status}->{msg}")

            return JSONResponse({
                # 'success': True,
                'message': '2FA successfully enabled!',
            }, status_code=200)


        return JSONResponse({
            # 'success': False,
            'message': 'Invalid verification code',
        }, status_code=HTTP_400_BAD_REQUEST)


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

@webApp.post("/account/security/password-reset/{uid}")
async def password_reset(uid: str, data: Annotated[passwordResetForm, Form()], session: SessionDep):
    user = get_user_by_id(uid, session)
    if user is None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid user")

    # Check if verification_code_hash is provided (forgot password flow)
    if data.verification_code_hash and data.verification_code_hash.strip() and data.verification_code_hash != 'None':
        # Forgot password flow - verify email code
        if user.code_expires_at is None:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="No verification code found. Please request a new one.")

        if user.code_expires_at < datetime.now():
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Verification code has expired. Please request a new one.")

        if not secure_password.verify(str(data.verification_code), str(data.verification_code_hash)):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid verification code")
    else:
        # Account center flow - verify 2FA code
        if not verify2FAcode(uid, str(data.verification_code), session):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid 2FA code")

    user.password = secure_password.hash(data.new_pswd)
    stats, msg = update_user(user, session)
    if stats == 500:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "msg": "Failed to update password",
                "error": msg
            }
        )

    pswd_update_confirm_email_template = templates.get_template("email/passwordUpdateConfirmation.html")
    email_stats, msg = send_email(
        to=user.email,
        subject="N.I.X Password Update Confirmation",
        body=pswd_update_confirm_email_template.render()
    )
    if email_stats is False:
        print(f"Email Sent Status: {stats}->{msg}")

    return stats


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
