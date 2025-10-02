from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.auth import login_required, verify2FAcode
from app.core.jwt_utility import generate_token
from app.core.emailing import send_email
from app.core.config import templates

from app.models.users import Token
from app.models import SessionDep, get_user, get_user_by_id, register_token, delete_user, update_user

from . import userApi, login
from .forms import loginForm

from typing import Union
from uuid import uuid4



@userApi.post("/auth/login")
async def user_login(login_data: loginForm, session: SessionDep):
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


@userApi.put('/auth/2FA/manage')
@login_required()
async def manage_2FA(req: Request, session: SessionDep, action: Union[bool, None], current_user_uid: str|None=None):
    user = get_user_by_id(str(current_user_uid), session)
    if user is None:
        return JSONResponse({"message": 'User Not found'}, status_code=404)

    if action is None:
        return JSONResponse({'message': 'Action not defined'}, status_code=400)

    user.is_2FA_enabled = action
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
