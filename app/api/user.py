from fastapi.responses import JSONResponse

from app.core.jwt_utility import generate_token

from app.models.users import Token
from app.models import SessionDep, get_user, register_token

from . import userApi, login
from .forms import loginForm

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
