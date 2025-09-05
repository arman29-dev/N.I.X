from fastapi import APIRouter

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
