from fastapi import APIRouter, Request

from app.core.config import DEVICE_QRCODE_ROOT_DIR

from os.path import join
from qrcode import QRCode
from typing import Literal


deviceApi = APIRouter(
    prefix="/api/v1/device",
    tags=["Device API"],
)


def generate_device_qr(req: Request, **kwargs) -> tuple[Literal[200, 500], bool, str]:
    qr = QRCode(
        version=1,
        box_size=10,
        border=1
    )

    for key, value in kwargs.items():
        qr.add_data(f'{key}:{value}\n')

    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    try:
        qr_file_path = join(DEVICE_QRCODE_ROOT_DIR, f'{kwargs['device_uid']}.png')
        with open(qr_file_path, 'wb') as f:
            img.save(f)

        return 200, True, str(req.url_for('static', path=f'device-QRs/{kwargs['device_uid']}.png'))

    except Exception as E:
        return 500, False, str(E)
