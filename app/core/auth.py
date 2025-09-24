from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse

from starlette.status import HTTP_302_FOUND

from app.models import SessionDep, get_user_by_id, get_user, get_session
from app.models.users import User
from app.core.jwt_utility import verify_token

from sqlmodel import Session
from functools import wraps
from pyotp import TOTP


security = HTTPBearer()


def check_access(credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)) -> User|None:
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = get_user(str(payload.get('sub')), session)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def login_required(redirect_url: str = "/web/home"):
    def decorator(func):
        @wraps(func)
        async def wrapper(req: Request, *args, **kwargs):
            user_logged_in = False
            current_user_uid = None

            for uid, email in req.session.items():
                if uid and isinstance(uid, str):
                    session = kwargs.get('session')
                    if session:
                        user = get_user_by_id(uid, session)
                        if user and user.email == email:
                            user_logged_in = True
                            current_user_uid = uid
                            break

            if not user_logged_in:
                return RedirectResponse(redirect_url, status_code=HTTP_302_FOUND)

            kwargs['current_user_uid'] = current_user_uid
            return await func(req, *args, **kwargs)

        return wrapper
    return decorator


def verify2FAcode(uid: str, code: str, session: SessionDep) -> bool:
    user = get_user_by_id(uid, session)
    if user is not None:
        totp = TOTP(str(user.twoFA_secret))
        if totp.verify(code):
            return True

    return False
