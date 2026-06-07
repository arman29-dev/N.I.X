import re
from fastapi import BackgroundTasks, Request, Query, Form, Depends
from fastapi.responses import JSONResponse

from app.core.auth import check_access, verify2FAcode, generate_verification_code
from app.core.jwt_utility import generate_token
from app.core.config import templates, limiter
from app.core.emailing import send_email

from app.models.users import User, Token
from app.models import SessionDep, get_user, get_user_by_id, get_user_devices, register_user, register_token, delete_user, update_user

from app.core.sLogger import security_logger

from app.web import webApp

from . import userApi, login
from .forms import apiLoginForm, loginForm, registerForm, passwordResetForm
from .comms import manager

from passlib.hash import pbkdf2_sha256 as secure_password
from datetime import datetime, timedelta
from pyotp import random_base32
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
        jwt = generate_token({
            'sub': data.email, 'uid': user.uid,
            'exp': datetime.now() + timedelta(days=30)
        })

        return JSONResponse({
            "is2FAenabled": twoFA_enable_stats,
            "redirectUrl": str(dashboardUrl),
            "authToken": jwt,
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
async def password_reset(uid: str, data: Annotated[passwordResetForm, Form()], background_tasks: BackgroundTasks, session: SessionDep):
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

    email_body = templates.get_template("email/passwordUpdateConfirmation.html").render()
    background_tasks.add_task(
        send_email,
        to=user.notification_email or user.email,
        subject="N.I.X Password Update Confirmation",
        body=email_body,
    )

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
async def send_reset_code(req: Request, background_tasks: BackgroundTasks, session: SessionDep):
    data = await req.json()
    email = data.get('email')
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

    email_body = templates.get_template("email/passwordResetCode.html").render(code=code)
    background_tasks.add_task(
        send_email,
        to=user.notification_email or email,
        subject="N.I.X Password Reset",
        body=email_body,
    )

    pswd_rst_url = req.url_for('password_reset_form', uid=user.uid).include_query_params(code=secure_password.hash(code))
    return JSONResponse({"endpoint": str(pswd_rst_url)}, status_code=200)


@userApi.post('/auth/2FA/setup')
async def verify2FA(req: Request, background_tasks: BackgroundTasks, session: SessionDep):
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

        email_body = templates.get_template("email/welcome.html").render(user=user)
        background_tasks.add_task(
            send_email,
            to=user.notification_email or user.email,
            subject="Welcome to N.I.X",
            body=email_body,
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

    jwt = generate_token({
        'sub': email, 'uid': user.uid,
        'exp': datetime.now() + timedelta(days=30)
    })

    return JSONResponse({
        "redirectUrl": str(req.url_for('dashboard', uid=user.uid)),
        "authToken": jwt,
    }, 200)


@userApi.get('/auth/2FA/toggle-setting')
async def toggle2FA(session: SessionDep, code: str | None = Query(None), user=Depends(check_access)):
    user = get_user_by_id(str(user.uid), session)
    if user is None:
        return JSONResponse({"message": 'User Not found'}, status_code=404)

    # Require valid 2FA code to disable
    if user.is_2FA_enabled:
        if not code or not verify2FAcode(user.uid, code, session):
            return JSONResponse({"message": 'Invalid 2FA code'}, status_code=401)

    user.is_2FA_enabled = not user.is_2FA_enabled
    stats, msg = update_user(user, session)

    await manager.send_to_user(user.uid, {
        "type": "event",
        "event": "2fa_toggled",
        "data": {"is_enabled": user.is_2FA_enabled}
    })

    return JSONResponse({'message': msg}, status_code=stats)



@userApi.put("/preferences/notification-email")
async def update_notification_email(req: Request, session: SessionDep, user=Depends(check_access)):
    user = get_user_by_id(str(user.uid), session)
    if user is None:
        return JSONResponse({"message": "User not found"}, status_code=404)

    data = await req.json()
    email_val = data.get("notification_email", "").strip()

    if email_val == "":
        email_val = None
    elif not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email_val):
        return JSONResponse({"message": "Invalid email format"}, status_code=400)

    user.notification_email = email_val
    stats, msg = update_user(user, session)
    if stats != 200:
        return JSONResponse({"message": msg}, status_code=stats)

    return JSONResponse({"message": "Notification email updated", "notification_email": email_val}, status_code=200)


@userApi.delete('/account/manage/delete-account')
async def delete_account(req: Request, background_tasks: BackgroundTasks, session: SessionDep, user=Depends(check_access)):
    data = await req.json()
    twofa_code = data.get('twofa_code')

    if user is None:
        return JSONResponse({'message': 'Authentication Failure!'}, status_code=401)

    if not verify2FAcode(user.uid, twofa_code, session):
        return JSONResponse({'message': 'Invalid 2FA code'}, status_code=401)

    user = get_user_by_id(user.uid, session)
    if user is None:
        return JSONResponse({'message': 'User not found'}, status_code=404)

    # Get devices before deletion for WS cleanup
    devices = get_user_devices(user.uid, session) or []

    # Tell each device to log out before deleting
    for device in devices:
        await manager.send_to_device(str(device.uid), {
            "type": "command",
            "action": "logout"
        })

    stats, msg = delete_user(user.uid, session)
    if stats == 200:
        # Disconnect device WS connections
        for device in devices:
            await manager.disconnect_device(str(device.uid))
            removed_msg = {"uid": str(device.uid)}
            await manager.send_to_user(user.uid, {
                "type": "event", "event": "device_removed", "data": removed_msg
            })

        email_body = templates.get_template("email/accountDeletion.html").render(user=user, loginFormUrl=req.url_for('home'))
        background_tasks.add_task(
            send_email,
            to=user.notification_email or user.email,
            subject="N.I.X Account Deletion",
            body=email_body,
        )

    return JSONResponse({'message': msg}, status_code=stats)
