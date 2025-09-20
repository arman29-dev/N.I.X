from fastapi import Request, Form, Depends
from fastapi.responses import JSONResponse

from app.core.config import SECRET_KEY
from app.core.auth import login_required, check_access

from app.models import SessionDep, get_user_access_token, register_device
from app.models.devices import Device

from . import deviceApi, generate_device_qr
from .forms import deviceForm

from uuid import UUID, uuid4
from typing import Annotated



@deviceApi.post("/util/generate-qr")
@login_required()
async def show_device_qr(req: Request, device_type: Annotated[str, Form()], session: SessionDep, current_user_uid: str|None=None):
    if current_user_uid is None:
        return JSONResponse(
            {
                'success': False,
                'message': 'Unauthorized'
            }, status_code=401
        )

    if device_type == "smartphone":
        user_access_token = get_user_access_token(current_user_uid, session)
        if user_access_token is None:
            return JSONResponse({
                'success': False,
                'message': 'Please login to the mobile app first.'
            }, status_code=401)

        status_code, stats, data = generate_device_qr(
            device_uid=str(uuid4()), secret=SECRET_KEY,
            user_access_token=user_access_token, req=req,
        )

        return JSONResponse({
            'success': stats,
            'qr_path': data,
        }, status_code=status_code)



@deviceApi.post('/manage/add-device')
async def add_device(device_data: deviceForm, session: SessionDep, user=Depends(check_access)):
    device = Device(
        uid=UUID(device_data.uid),
        name=device_data.name,
        type=device_data.type,
        ip=device_data.ip,
        owner=device_data.owner
    )

    stats, meg = register_device(device, session)
    if stats != 200:
        return JSONResponse({'stats': stats, 'message': meg}, status_code=stats)

    return JSONResponse({'stats': stats, 'message': meg}, status_code=stats)
