from fastapi import Request, Form
from fastapi.responses import JSONResponse

from app.core.auth import login_required, verify2FAcode, generate_verification_code
from app.core.jwt_utility import generate_token
from app.core.config import templates, limiter
from app.core.emailing import send_email

from app.models.users import User, Token
from app.models import SessionDep, get_user, get_user_by_id, register_user, register_token, delete_user, update_user

from app.core.sLogger import security_logger

from app.web import webApp

from . import userApi, login
from .forms import apiLoginForm, loginForm, registerForm, passwordResetForm

from passlib.hash import pbkdf2_sha256 as secure_password
from pyotp import random_base32
from datetime import datetime
from typing import Annotated
from uuid import uuid4



# Login Route
@webApp.post("/auth/login/")
@limiter.limit("5/minute")
async def web_login(request: Request, data: Annotated[loginForm, Form()], session: SessionDep):
    client_ip = request.client.host if request.client else 'unknown'

    security_logger.info(f"Login attempt for email: {data.email} from IP: {client_ip}")

    user = get_user(data.email, session)
    if user is None:
        security_logger.warning(f"Failed login attempt - user not found: {data.email} from IP: {client_ip}")

        return JSONResponse({
            "loginError": "Invalid email or not registered"
        }, status_code=404)

    if not secure_password.verify(data.password, user.password):
        security_logger.warning(f"Failed login attempt - incorrect password for: {data.email} from IP: {client_ip}")

        return JSONResponse({
            "loginError": "Incorrect password for this account"
        }, status_code=401)

    dashboardUrl = request.url_for('dashboard', uid=user.uid)
    twoFA_enable_stats = user.is_2FA_enabled

    if twoFA_enable_stats:
       return JSONResponse({
           "is2FAenabled": twoFA_enable_stats,
           "redirectUrl": str(dashboardUrl),
           "twoFAverificationEndpoint": str(request.url_for('web2FAverification'))
       }, status_code=302)

    else:
        security_logger.info(f"Successful login for: {data.email} from IP: {client_ip}")
        request.session[user.uid] = data.email
        return JSONResponse({
            "is2FAenabled": twoFA_enable_stats,
            "redirectUrl": str(dashboardUrl)
        }, status_code=302)


# Register Route
@webApp.post("/auth/register/")
async def web_register(req: Request, data: Annotated[registerForm, Form()], session: SessionDep):
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
        return JSONResponse({
            "redirectUrl": str(req.url_for('setup_2FA', uid=user.uid))
        }, status_code=status)

    elif status == 500:
        security_logger.error(f"Registration failed for {data.email}: {msg}",
            exc_info=True, extra={'client_ip': client_ip}
        )

        return JSONResponse({
                "error": msg
            }, status_code=status)


@webApp.put("/account/security/password-reset/{uid}")
async def password_reset(uid: str, data: Annotated[passwordResetForm, Form()], session: SessionDep):
    user = get_user_by_id(uid, session)
    if user is None:
        return JSONResponse({
            "msg": "Account not found"
        }, status_code=404)

    # Check if verification_code_hash is provided (forgot password flow)
    if data.verification_code_hash and data.verification_code_hash.strip() and data.verification_code_hash != 'None':
        if user.code_expires_at is None:
            return JSONResponse({
                "msg": "No verification code found. Please request a new one."
            }, status_code=400)

        if user.code_expires_at < datetime.now():
            return JSONResponse({
                "msg": "Verification code has expired. Please request a new one."
            }, status_code=400)

        if not secure_password.verify(str(data.verification_code), str(data.verification_code_hash)):
            return JSONResponse({
                "msg": "Invalid verification code"
            }, status_code=400)
    else:
        if not verify2FAcode(uid, str(data.verification_code), session):
            return JSONResponse({
                "msg": "Invalid 2FA code"
            }, status_code=400)

    user.password = secure_password.hash(data.new_pswd)
    stats, msg = update_user(user, session)
    if stats == 500:
        return JSONResponse({
            "msg": "Failed to update password",
            "error": msg
        }, status_code=stats)

    pswd_update_confirm_email_template = templates.get_template("email/passwordUpdateConfirmation.html")
    email_stats, msg = send_email(
        to=user.email,
        subject="N.I.X Password Update Confirmation",
        body=pswd_update_confirm_email_template.render()
    )
    if email_stats is False:
        print(f"Email Sent Status: {stats}->{msg}")

    return JSONResponse({
        "msg": "Success"
    }, status_code=200)


@userApi.post("/auth/login")
async def user_login(login_data: apiLoginForm, session: SessionDep):
    user = get_user(login_data.email, session)
    if user is None:
        return JSONResponse({'Error': 'User not found'}, status_code=401)

    stats, msg = login(user, session, **login_data.model_dump())
    if stats == 200:
        access_token = generate_token({'sub': user.email, 'uid': user.uid})
        access_token_uid = uuid4()
        token = Token(uid=access_token_uid, owner=user.uid, access_token=access_token)
        tkn_reg_stats, tkn_reg_msg = register_token(token, session)

        msg.update(
            {
                'access_token': access_token,
                'access_token_uid': str(access_token_uid),
                'token_type': 'Bearer'
            }
        )

        if tkn_reg_stats != 200:
            return JSONResponse({'Error': tkn_reg_msg}, status_code=tkn_reg_stats)

    return JSONResponse(msg, status_code=stats)


@userApi.post("/account/security/forgot-password")
async def send_reset_code(req: Request, email: Annotated[str, Form()], session: SessionDep):
    user = get_user(email, session)
    if user is None:
        return JSONResponse({
            "error": "No account found with this email"
        }, status_code=404)

    code = generate_verification_code(user, session)
    if code is None:
        return JSONResponse({
            "error": "Failed to generate verification code. Please try again."
        }, status_code=500)

    pswdreset_email_template = templates.get_template("email/passwordResetCode.html")
    email_stats, msg = send_email(
        to=email,
        subject="N.I.X Password Reset",
        body=pswdreset_email_template.render(code=code)
    )

    if email_stats is False:
        return JSONResponse({"error": f"Failed to send email: {msg}"}, status_code=500)

    pswd_rst_url = req.url_for('password_reset_form', uid=user.uid).include_query_params(code=secure_password.hash(code))
    return JSONResponse({"endpoint": str(pswd_rst_url)}, status_code=200)


@userApi.post('/auth/2FA/setup')
async def verify2FA(req: Request, session: SessionDep):
    reqData = await req.json()
    code = reqData.get('code')
    email = reqData.get('email')

    user = get_user(email, session)
    if user is None:
        return JSONResponse({
            "message": "User not found!"
        }, status_code=400)

    if verify2FAcode(user.uid, code, session):
        req.session[user.uid] = user.email

        email_template = templates.get_template("email/welcome.html")
        send_email(
            to=user.email,
            subject="Welcome to N.I.X",
            body=email_template.render(user=user)
        )

        return JSONResponse({
            'message': '2FA successfully enabled!',
        }, status_code=200)


    return JSONResponse({
        'message': 'Invalid verification code',
    }, status_code=401)


@webApp.post('/auth/2FA/verify')
async def web2FAverification(req: Request, session: SessionDep):
    client_ip = req.client.host if req.client else 'unknown'

    reqData = await req.json()
    code = reqData.get('code')
    email = reqData.get('email')

    user = get_user(email, session)
    if user is None:
        return JSONResponse({
            "loginError": "User not found with this email!"
        }, status_code=404)

    if verify2FAcode(user.uid, code, session) is not True:
        security_logger.warning(f"Failed login attempt - invalid 2FA code for: {email} from IP: {client_ip}")

        return JSONResponse({
            "loginError": "Invalid 2FA code"
        }, status_code=401)

    security_logger.info(f"Successful login for: {email} from IP: {client_ip}")
    req.session[user.uid] = email

    return JSONResponse({
        "redirectUrl": str(req.url_for('dashboard', uid=user.uid))
    }, 200)


@userApi.get('/auth/2FA/toggle-setting')
@login_required()
async def toggle2FA(req: Request, session: SessionDep, current_user_uid: str|None=None):
    user = get_user_by_id(str(current_user_uid), session)
    if user is None:
        return JSONResponse({"message": 'User Not found'}, status_code=404)

    user.is_2FA_enabled = not user.is_2FA_enabled
    stats, msg = update_user(user, session)

    return JSONResponse({'message': msg}, status_code=stats)


@userApi.delete('/account/manage/delete-account')
@login_required()
async def delete_account(req: Request, session: SessionDep, current_user_uid: str|None=None):
    data = await req.json()
    twofa_code = data.get('twofa_code')

    if current_user_uid is None:
        return JSONResponse({'message': 'Authentication Failure!'}, status_code=401)

    if not verify2FAcode(current_user_uid, twofa_code, session):
        return JSONResponse({'message': 'Invalid 2FA code'}, status_code=401)

    user = get_user_by_id(current_user_uid, session)
    if user is None:
        return JSONResponse({'message': 'User not found'}, status_code=404)

    stats, msg = delete_user(current_user_uid, session)
    if stats == 200:
        email_template = templates.get_template("email/accountDeletion.html")
        send_email(
            to=user.email,
            subject="N.I.X Account Deletion",
            body=email_template.render(user=user, loginFormUrl=req.url_for('home'))
        )

    return JSONResponse({'message': msg}, status_code=stats)
