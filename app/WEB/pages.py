from fastapi import Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.status import HTTP_302_FOUND, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.models import SessionDep, get_user, get_user_by_id, register_user, update_user
from app.core.config import templates, AUTH_QRCODE_ROOT_DIR
from app.core.emailing import send_email
from app.models.users import User

from . import webApp, get_2FA_uri, verify2FAcode, login_required, generate_verification_code
from .forms import loginForm, registerForm, twoFactorAuthForm, passwordResetForm

from passlib.hash import pbkdf2_sha256 as secure_password
from typing import Annotated, Union
from pyotp import random_base32
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
    return RedirectResponse(req.url_for('dashboard', uid=user.uid), status_code=HTTP_302_FOUND)

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

            email_template = templates.get_template("email/welcome.html")
            status, msg = send_email(
                to=user.email,
                subject="Welcome to N.I.X",
                body=email_template.render(user=user)
            )
            if status is not True:
                print(f"Email Sent Status: {status}->{msg}")

            return JSONResponse({
                'success': True,
                'message': '2FA enabled successfully',
            })


        return JSONResponse({
            'success': False,
            'message': 'Invalid verification code',
        }, status_code=HTTP_400_BAD_REQUEST)


# Forgot Password Route
@webApp.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password(req: Request):
    return templates.TemplateResponse(
        "forgot-password.html",
        {"request": req}
    )

@webApp.post("/forgot-password")
async def send_reset_code(email: Annotated[str, Form()], session: SessionDep):
    user = get_user(email, session)
    if user is None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Email not registered")

    code = generate_verification_code(user, session)
    if code is None:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification code"
        )

    pswdreset_email_template = templates.get_template("email/passwordResetCode.html")
    email_stats, msg = send_email(
        to=email,
        subject="N.I.X Password Reset",
        body=pswdreset_email_template.render(code=code)
    )

    if email_stats is False:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "msg": "Failed to send password rest code email",
                "error": msg
            }
        )

    return RedirectResponse(f"/web/password-reset/{user.uid}?code={secure_password.hash(code)}", status_code=HTTP_302_FOUND)


# Password Reset Route
@webApp.get("/password-reset/{uid}", response_class=HTMLResponse)
async def password_reset_form(req: Request, uid: str, code: Union[str, None], session: SessionDep):
    user = get_user_by_id(uid, session)
    if user is None:
        return RedirectResponse("/web/forgot-password", status_code=HTTP_302_FOUND)

    return templates.TemplateResponse(
        "password-reset.html",
        {
            "request": req,
            "uid": user.uid,
            "code_hash": code
        }
    )

@webApp.post("/password-reset/{uid}")
async def password_reset(uid: str, data: Annotated[passwordResetForm, Form()], session: SessionDep):
    user = get_user_by_id(uid, session)
    if user is None:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid user")

    # Verify the verification code against the stored code
    if not secure_password.verify(str(data.verification_code), str(data.verification_code_hash)):
        if not verify2FAcode(uid, str(data.verification_code), session):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid verification code")

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
    if stats is False:
        print(f"Email Sent Status: {stats}->{msg}")

    return stats


# Logout Route
@webApp.get("/logout/")
@login_required()
async def logout(req: Request, session: SessionDep, current_user_uid: str|None=None):
    req.session.pop(str(current_user_uid))
    return RedirectResponse("/web/home", status_code=HTTP_302_FOUND)


# Dashboard Route
@webApp.get("/dashboard/{uid}", response_class=HTMLResponse)
@login_required()
async def dashboard(req: Request, uid: str, session: SessionDep, current_user_uid: str|None=None):
    return JSONResponse({
        "success": True,
        "message": f"Welcome to your dashboard, {uid}!"
    }, status_code=HTTP_302_FOUND)
