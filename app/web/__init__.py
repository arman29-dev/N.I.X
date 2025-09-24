from fastapi import APIRouter, Request

from app.models import SessionDep, get_user_by_id, update_user
from app.models.users import User

from pyotp import TOTP
from secrets import choice
from datetime import timedelta, datetime



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


def generate_verification_code(user: User, session: SessionDep, expiry_minutes=5) -> str:
        code = ''.join(choice('0123456789') for _ in range(6))
        user.verification_code = code
        user.code_expires_at = datetime.now() + timedelta(minutes=expiry_minutes)

        stats, msg = update_user(user, session)
        if stats == 200:
            return code
        else:
            return msg
