from fastapi import APIRouter

from app.core.auth import verify2FAcode

from app.models import SessionDep
from app.models.users import User

from typing import Literal
from passlib.hash import pbkdf2_sha256 as password




deviceApi = APIRouter(
    prefix="/api/v1/device",
    tags=["Device API"],
)

userApi = APIRouter(
    prefix="/api/v1/user",
    tags=["User API"],
)



def login(user: User, session: SessionDep, **credentials) -> tuple[Literal[200, 401], dict]:
    if not password.verify(credentials['password'], user.password):
        return 401, {'Error': 'Invalid password'}

    if not verify2FAcode(user.uid, str(credentials['twoFA']), session):
        return 401, {'Error': 'Invalid 2FA code'}

    return 200, {'success': True}
