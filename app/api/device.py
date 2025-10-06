from fastapi import Request, Form, Depends
from fastapi.responses import JSONResponse
from sqlmodel import select

from app.core.config import SECRET_KEY
from app.core.auth import login_required, check_access, get_qrcode, verify2FAcode

from app.models import SessionDep, delete_device, delete_device_registered_token, delete_token, get_device, get_user_access_token, register_device, get_user_devices
from app.models.devices import Device
from app.models.users import Token

from . import deviceApi
from .forms import deleteDeviceForm, deviceForm

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

        status_code, data = get_qrcode(qr_for='device',
            device_uid=str(uuid4()), secret=SECRET_KEY,
            user_access_token=user_access_token
        )

        return JSONResponse({
            'qr_path': data,
        }, status_code=status_code)


@deviceApi.post('/manage/add-device')
async def add_device(device_data: deviceForm, session: SessionDep, user=Depends(check_access)):
    device_uid = UUID(device_data.uid)
    device = Device(
        uid=device_uid,
        name=device_data.name,
        type=device_data.type,
        ip=device_data.ip,
        owner=device_data.owner
    )

    try:
        token_uid = UUID(device_data.token_ID)
        statement = select(Token).where(Token.uid == token_uid, Token.owner == user.uid)
        token = session.exec(statement).first()

        if token is None:
            return JSONResponse({'stats': 404, 'msg': 'Token not found'}, status_code=404)

        # Create new token for this device if current token is already linked
        if token.linked_device and token.linked_device != 'xxxxx-xxx-xxx-xxxxx':
            from uuid import uuid4
            from datetime import datetime, timedelta

            new_token = Token(
                uid=uuid4(),
                owner=user.uid,
                access_token=token.access_token,  # Reuse same JWT
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=30),
                linked_device=str(device_uid)
            )
            session.add(new_token)
        else:
            token.linked_device = str(device_uid)
            session.add(token)

        session.commit()

    except Exception as E:
        return JSONResponse({'msg': str(E)}, status_code=500)

    stats, msg = register_device(device, session)
    if stats != 200:
        return JSONResponse({'stats': stats, 'msg': msg}, status_code=stats)

    return JSONResponse(
        {
            'stats': stats, 'msg': msg,
            'device_status': device.is_active
        }, status_code=stats
    )


@deviceApi.get('/manage/toggle-status')
async def toggleStatus(uid: str, session: SessionDep, user=Depends(check_access)):
    if user is None:
        return JSONResponse({
            "msg": "User not Found!"
        }, status_code=404)

    statement = select(Device).where(Device.owner == user.uid, Device.uid == UUID(uid))
    device = session.exec(statement).first()

    if device is None:
        return JSONResponse({
            "msg": "Device not Found!"
        }, status_code=404)

    device.is_active = not device.is_active

    session.add(device)
    session.commit()
    session.refresh(device)

    return JSONResponse({
        "msg": "Status updated!",
        "device_status": device.is_active
    }, status_code=200)


@deviceApi.post('/manage/logout')
async def deregister_device(delete_info: deleteDeviceForm, session: SessionDep, user=Depends(check_access)):
    if delete_info.access_token_uid and delete_info.device_uid is not None:

        device = get_device(delete_info.device_uid, user.uid, session)
        if device is None:
            return JSONResponse({'msg': 'No device found'}, status_code=500)

        dd_stats, dd_msg = delete_device(delete_info.device_uid, user.uid, session)
        if dd_stats == 200:
            atd_stats, atd_msg = delete_device_registered_token(delete_info.access_token_uid, device, session)

            return JSONResponse({'msg': [dd_msg, atd_msg]}, status_code=atd_stats)

    return JSONResponse({'msg': 'No logout data provided'}, status_code=500)


@deviceApi.delete('/manage/delete-all')
@login_required()
async def delete_all_devices(req: Request, session: SessionDep, current_user_uid: str|None=None):
    data = await req.json()
    twofa_code = data.get('twofa_code')

    if current_user_uid is None:
        return JSONResponse({'message': 'Authentication Failure!'}, status_code=401)

    if not verify2FAcode(current_user_uid, twofa_code, session):
        return JSONResponse({'message': 'Invalid 2FA code'}, status_code=401)

    devices = get_user_devices(current_user_uid, session)
    if devices is None:
        return JSONResponse({'message': 'Unable to fetch devices fot this action!'}, status_code=500)

    for device in devices:
        delete_device(str(device.uid), current_user_uid, session)
        delete_token(current_user_uid, session)


    return JSONResponse({'message': 'All devices deleted successfully'}, status_code=200)
