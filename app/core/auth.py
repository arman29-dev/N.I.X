from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse

from sqlalchemy.util.typing import Literal
from starlette.status import HTTP_302_FOUND

from app.models.users import User
from app.core.jwt_utility import verify_token
from app.models import SessionDep, get_user_by_id, get_user, get_session, update_user

from datetime import timedelta, datetime
from sqlmodel import Session
from base64 import b64encode
from functools import wraps
from secrets import choice
from qrcode import QRCode
from io import BytesIO
from pyotp import TOTP
from json import dumps



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


def generate_verification_code(user: User, session: SessionDep, expiry_minutes=5) -> str:
        code = ''.join(choice('0123456789') for _ in range(6))
        user.verification_code = code
        user.code_expires_at = datetime.now() + timedelta(minutes=expiry_minutes)

        stats, msg = update_user(user, session)
        if stats == 200:
            return code
        else:
            return msg


def get_qrcode(qr_for: str='2FA', data: str|None=None, **kwargs) -> tuple[Literal[200, 500], str]:
    if qr_for == 'device':
        required_fields = ['device_uid', 'secret', 'user_access_token']
        for field in required_fields:
            if field not in kwargs or kwargs[field] is None:
                return 500, f"Missing required field: {field}"

    qr = QRCode(
        version=1,
        box_size=10,
        border=1
    )

    if kwargs:
        qr.add_data(dumps(kwargs))
    if data is not None:
        qr.add_data(data)

    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    try:
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        qr_base64 = b64encode(img_io.getvalue()).decode()

        return 200, f'data:image/png;base64,{qr_base64}'

    except Exception as E:
        return 500, str(E)
