from fastapi import Request, Depends
from fastapi.responses import JSONResponse, Response
from sqlmodel import select
from datetime import datetime, timedelta

from app.core.config import SECRET_KEY
from app.core.auth import check_access, get_qrcode, verify2FAcode
from app.core.crypto import encrypt_config
from app.core.jwt_utility import generate_token

from app.models import (
    SessionDep, delete_device, delete_device_registered_token, delete_token,
    get_device, get_user_access_token, register_device, register_token,
    get_user_devices
)
from app.models.devices import Device
from app.models.users import Token

from . import deviceApi
from .forms import deleteDeviceForm, deviceForm
from .comms import manager

from uuid import UUID, uuid4



@deviceApi.post("/util/generate-qr")
async def show_device_qr(req: Request, session: SessionDep, user=Depends(check_access)):
    if user is None:
        return JSONResponse(
            {
                'success': False,
                'message': 'Unauthorized'
            }, status_code=401
        )

    data = await req.json()
    device_type = data.get('device_type')

    # Shared: get or create access token
    token_data = get_user_access_token(user.uid, session)
    if token_data is None:
        access_token = generate_token({'sub': user.email, 'uid': user.uid})
        access_token_uid = uuid4()
        token = Token(uid=access_token_uid, owner=user.uid, access_token=access_token,
                      created_at=datetime.now(), expires_at=datetime.now() + timedelta(days=30))
        tkn_stats, tkn_msg = register_token(token, session)
        if tkn_stats != 200:
            return JSONResponse({'success': False, 'message': tkn_msg}, status_code=500)
        user_access_token = access_token
        token_uid = str(access_token_uid)
    else:
        user_access_token, token_uid = token_data

    device_uid = str(uuid4())
    payload = {
        'device_uid': device_uid,
        'user_access_token': user_access_token,
        'access_token_uid': token_uid,
        'owner_uid': user.uid,
    }

    if device_type == "smartphone":
        status_code, qr_data = get_qrcode(qr_for='device', **payload)
        return JSONResponse({
            'qr_path': qr_data,
        }, status_code=status_code)

    elif device_type == "laptop":
        encrypted = encrypt_config(payload, SECRET_KEY)
        return Response(
            content=encrypted,
            media_type='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="nix-config-{device_uid[:8]}.nixconfig"',
            },
        )


@deviceApi.post('/manage/add-device')
async def add_device(device_data: deviceForm, session: SessionDep, user=Depends(check_access)):
    device_uid = UUID(device_data.uid)

    existing = get_device(str(device_uid), user.uid, session)
    if existing is not None:
        return JSONResponse({'msg': 'Device already registered'}, status_code=409)

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

    device_added_msg = {
        "uid": str(device.uid),
        "name": device.name,
        "type": device.type,
        "ip": device.ip,
        "is_active": device.is_active,
    }
    await manager.send_to_user(user.uid, {
        "type": "event", "event": "device_added", "data": device_added_msg
    })
    await manager.send_to_user_device(user.uid, {
        "type": "event", "event": "device_added", "data": device_added_msg
    })

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

    status_change_msg = {
        "uid": str(device.uid),
        "is_active": device.is_active,
    }
    await manager.send_to_user(user.uid, {
        "type": "event", "event": "device_status_change", "data": status_change_msg
    })
    await manager.send_to_user_device(user.uid, {
        "type": "event", "event": "device_status_change", "data": status_change_msg
    })

    return JSONResponse({
        "msg": "Status updated!",
        "device_status": device.is_active
    }, status_code=200)


@deviceApi.post('/manage/logout')
async def deregister_device(delete_info: deleteDeviceForm, session: SessionDep, user=Depends(check_access)):
    if not delete_info.access_token_uid or not delete_info.device_uid:
        return JSONResponse({'msg': 'No logout data provided'}, status_code=500)

    device = get_device(delete_info.device_uid, user.uid, session)
    if device is None:
        return JSONResponse({'msg': 'No device found'}, status_code=500)

    # Tell the device to log out before removing it
    await manager.send_to_device(delete_info.device_uid, {
        "type": "command",
        "action": "logout"
    })

    dd_stats, dd_msg = delete_device(delete_info.device_uid, user.uid, session)
    if dd_stats != 200:
        return JSONResponse({'msg': dd_msg}, status_code=dd_stats)

    delete_device_registered_token(delete_info.access_token_uid, session)

    removed_msg = {"uid": delete_info.device_uid}
    await manager.send_to_user(user.uid, {
        "type": "event", "event": "device_removed", "data": removed_msg
    })
    await manager.disconnect_device(delete_info.device_uid)

    return JSONResponse({'msg': 'Device deregistered successfully'}, status_code=200)


@deviceApi.delete('/manage/delete-all')
async def delete_all_devices(req: Request, session: SessionDep, user=Depends(check_access)):
    data = await req.json()
    twofa_code = data.get('twofa_code')

    if user is None:
        return JSONResponse({'message': 'Authentication Failure!'}, status_code=401)

    if not verify2FAcode(user.uid, twofa_code, session):
        return JSONResponse({'message': 'Invalid 2FA code'}, status_code=401)

    devices = get_user_devices(user.uid, session)
    if devices is None:
        return JSONResponse({'message': 'Unable to fetch devices fot this action!'}, status_code=500)

    for device in devices:
        # Tell the device to log out before removing it
        await manager.send_to_device(str(device.uid), {
            "type": "command",
            "action": "logout"
        })
        delete_device(str(device.uid), user.uid, session)
        delete_token(user.uid, session)
        removed_msg = {"uid": str(device.uid)}
        await manager.send_to_user(user.uid, {
            "type": "event", "event": "device_removed", "data": removed_msg
        })
        await manager.disconnect_device(str(device.uid))

    return JSONResponse({'message': 'All devices deleted successfully'}, status_code=200)
