from fastapi import APIRouter, Request

from app.models import SessionDep, get_user_by_id
from app.models.users import User

from pyotp import TOTP




webApp = APIRouter(
    prefix="/web",
    tags=["WebApp"],
)


def get_current_user(req: Request, session: SessionDep) -> User | None:
    for uid, email in req.session.items():
        if uid and isinstance(uid, str):
            user = get_user_by_id(uid, session)
            if user and user.email == email:
                return user
    return None


def get_2FA_uri(user: User) -> str|None:
    if user is not None:
        uri = TOTP(str(user.twoFA_secret)).provisioning_uri(
            name=user.email,
            issuer_name="N.I.X"
        )
        return uri

    return None
