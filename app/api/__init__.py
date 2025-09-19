from fastapi import APIRouter, Request

from app.core.auth import verify2FAcode
from app.core.config import DEVICE_QRCODE_ROOT_DIR

from app.models import SessionDep
from app.models.users import User

from json import dumps
from os.path import join
from qrcode import QRCode
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


def generate_device_qr(req: Request, **kwargs) -> tuple[Literal[200, 500], bool, str]:
    qr = QRCode(
        version=1,
        box_size=10,
        border=1
    )

    qr.add_data(dumps(kwargs))
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    try:
        qr_file_path = join(DEVICE_QRCODE_ROOT_DIR, f'{kwargs['device_uid']}.png')
        with open(qr_file_path, 'wb') as f:
            img.save(f)

        return 200, True, str(req.url_for('static', path=f'device-QRs/{kwargs['device_uid']}.png'))

    except Exception as E:
        return 500, False, str(E)


def login(user: User, session: SessionDep, **credentials) -> tuple[Literal[200, 401], dict]:
    if not password.verify(credentials['password'], user.password):
        return 401, {'Error': 'Invalid password'}

    if not verify2FAcode(user.uid, credentials['twoFA'], session):
        return 401, {'Error': 'Invalid 2FA code'}

    return 200, credentials
