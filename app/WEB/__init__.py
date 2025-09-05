from fastapi.responses import RedirectResponse
from starlette.status import HTTP_302_FOUND
from fastapi import APIRouter, Request
from functools import wraps

from app.models import SessionDep, get_user_by_id
from app.models.users import User

from pyotp import TOTP



webApp = APIRouter(
    prefix="/web",
    tags=[
        "Web", "WebApp",
        "N.I.X-Dashboard"
    ],
)


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


def get_current_user(req: Request, session: SessionDep) -> User | None:
    for uid, email in req.session.items():
        if uid and isinstance(uid, str):
            user = get_user_by_id(uid, session)
            if user and user.email == email:
                return user
    return None


def get_2FA_uri(user: User):
    if user is not None:
        uri = TOTP(str(user.twoFA_secret)).provisioning_uri(
            name=user.email,
            issuer_name="N.I.X"
        )
        return uri

    return None


def verify2FAcode(uid: str, code: str, session: SessionDep):
    user = get_user_by_id(uid, session)
    if user is not None:
        totp = TOTP(str(user.twoFA_secret))
        if totp.verify(code):
            return True

    return False
