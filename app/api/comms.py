from fastapi import WebSocket, WebSocketDisconnect, Query
from sqlmodel import select

from . import commsWS, WSConnectionManager
from app.core.auth import verify_ws_token, verify2FAcode
from app.models import get_session, get_user_by_id, get_user_devices
from app.models import update_device, delete_device as delete_device_db
from app.models import get_device as get_device_db
from app.models.devices import Device
from app.core.sLogger import security_logger

from uuid import UUID
from datetime import datetime, timezone
from logging import getLogger



logger = getLogger(__name__)
manager = WSConnectionManager()


# ── Existing Messaging WS (device-to-device chat) ──
@commsWS.websocket('/ws/comms/{user_id}/{device_id}')
async def comms(ws: WebSocket, user_id: str, device_id: str, token: str = Query(...)):
    payload = verify_ws_token(token)
    if not payload or payload.get('uid') != user_id:
        await ws.close(code=4001, reason="Unauthorized")
        return
    try:
        UUID(device_id)
    except ValueError:
        await ws.close(code=4004, reason="Invalid device ID")
        return
    session = next(get_session())
    try:
        device = session.exec(select(Device).where(Device.uid == UUID(device_id), Device.owner == user_id)).first()
        if not device:
            await ws.close(code=4004, reason="Device not found")
            return
    finally:
        session.close()

    await manager.connect_device(user_id, device_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            await manager.send_to_user(user_id, {
                "type": "event",
                "event": "device_message",
                "data": {"from_device": device_id, "message": data}
            })
    except WebSocketDisconnect:
        await manager.disconnect_device(device_id)


# ── Dashboard Events WS (browser) ──
@commsWS.websocket('/ws/events/{user_id}')
async def events_ws(ws: WebSocket, user_id: str, token: str = Query(...)):
    payload = verify_ws_token(token)
    if not payload or payload.get('uid') != user_id:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await manager.connect_user(user_id, ws)

    # Send snapshot of currently connected devices
    connected_ids = manager.get_user_connected_devices(user_id)
    await ws.send_json({
        "type": "event",
        "event": "device_connectivity_snapshot",
        "data": {"connected_uids": connected_ids}
    })

    try:
        while True:
            data = await ws.receive_json()
            action = data.get('action')

            if action == 'toggle_2fa':
                code = data.get('code')
                session = next(get_session())
                try:
                    user = get_user_by_id(user_id, session)
                    if not user:
                        await ws.send_json({"type": "error", "msg": "User not found"})
                        continue
                    # Require valid 2FA code to disable
                    if user.is_2FA_enabled:
                        if not code or not verify2FAcode(user.uid, code, session):
                            await ws.send_json({"type": "error", "msg": "Invalid 2FA code"})
                            continue
                    user.is_2FA_enabled = not user.is_2FA_enabled
                    from app.models import update_user
                    stats, _ = update_user(user, session)
                    if stats == 200:
                        security_logger.info(f"2FA toggled via WS for user: {user_id}")
                        await manager.send_to_user(user_id, {
                            "type": "event",
                            "event": "2fa_toggled",
                            "data": {"is_enabled": user.is_2FA_enabled}
                        })
                    else:
                        await ws.send_json({"type": "error", "msg": "Failed to toggle 2FA"})
                finally:
                    session.close()

            elif action == 'rename_device':
                device_uid = data.get('uid')
                new_name = data.get('name')
                if not device_uid or not new_name:
                    await ws.send_json({"type": "error", "msg": "Missing uid or name"})
                    continue
                session = next(get_session())
                try:
                    device = get_device_db(device_uid, user_id, session)
                    if not device:
                        await ws.send_json({"type": "error", "msg": "Device not found"})
                        continue
                    device.name = new_name
                    stats, _ = update_device(device, session)
                    if stats == 200:
                        renamed_msg = {"uid": device_uid, "name": new_name}
                        await manager.send_to_user(user_id, {
                            "type": "event", "event": "device_renamed", "data": renamed_msg
                        })
                        await manager.send_to_user_device(user_id, {
                            "type": "event", "event": "device_renamed", "data": renamed_msg
                        })
                    else:
                        await ws.send_json({"type": "error", "msg": "Failed to rename device"})
                finally:
                    session.close()

            elif action == 'refresh_devices':
                session = next(get_session())
                try:
                    all_devices = get_user_devices(user_id, session)
                    devices_data = []
                    for d in all_devices:
                        devices_data.append({
                            "uid": str(d.uid),
                            "name": d.name,
                            "type": d.type,
                            "ip": d.ip,
                            "is_active": d.is_active,
                        })
                    await ws.send_json({
                        "type": "event",
                        "event": "device_refresh",
                        "data": {"devices": devices_data}
                    })
                finally:
                    session.close()

            elif action == 'delete_device':
                device_uid = data.get('uid')
                if not device_uid:
                    await ws.send_json({"type": "error", "msg": "Missing uid"})
                    continue
                if manager.is_device_connected(device_uid):
                    await manager.send_to_device(device_uid, {"type": "command", "action": "logout"})
                    await manager.disconnect_device(device_uid)
                session = next(get_session())
                try:
                    stats, msg = delete_device_db(device_uid, user_id, session)
                    if stats == 200:
                        removed_msg = {"uid": device_uid}
                        await manager.send_to_user(user_id, {
                            "type": "event", "event": "device_removed", "data": removed_msg
                        })
                        await manager.send_to_user_device(user_id, {
                            "type": "event", "event": "device_removed", "data": removed_msg
                        })
                    else:
                        await ws.send_json({"type": "error", "msg": msg})
                finally:
                    session.close()

            elif action == 'send_direct_message':
                target_device = data.get('target_device')
                message = data.get('message', '')
                if not target_device:
                    await ws.send_json({"type": "error", "msg": "Missing target_device"})
                    continue
                if not message:
                    await ws.send_json({"type": "error", "msg": "Missing message"})
                    continue
                msg_payload = {"from_device": "web_dashboard", "message": message}
                if manager.is_device_connected(target_device):
                    await manager.send_to_device(target_device, {
                        "type": "event", "event": "device_message", "data": msg_payload
                    })
                    await ws.send_json({
                        "type": "event", "event": "device_message",
                        "data": {"from_device": "web_dashboard", "message": message, "target_device": target_device}
                    })
                else:
                    await ws.send_json({"type": "error", "msg": "Target device not connected"})

            elif action == 'get_devices':
                session = next(get_session())
                try:
                    from app.models import get_user_devices
                    all_devices = get_user_devices(user_id, session)
                    connected_ids = manager.get_user_connected_devices(user_id)
                    devices_data = []
                    for d in all_devices:
                        devices_data.append({
                            "uid": str(d.uid),
                            "name": d.name,
                            "type": d.type,
                            "ip": d.ip,
                            "is_active": d.is_active,
                            "is_online": str(d.uid) in connected_ids,
                        })
                    await ws.send_json({
                        "type": "event",
                        "event": "device_list",
                        "data": {"devices": devices_data}
                    })
                finally:
                    session.close()

    except WebSocketDisconnect:
        manager.disconnect_user(user_id, ws)
    except Exception:
        manager.disconnect_user(user_id, ws)


# ── Device Control WS (Flutter app) ──
@commsWS.websocket('/ws/device/{user_id}/{device_id}')
async def device_ws(ws: WebSocket, user_id: str, device_id: str, token: str = Query(...)):
    payload = verify_ws_token(token)
    if not payload or payload.get('uid') != user_id:
        await ws.close(code=4001, reason="Unauthorized")
        return
    try:
        UUID(device_id)
    except ValueError:
        await ws.close(code=4004, reason="Invalid device ID")
        return
    session = next(get_session())
    try:
        device = session.exec(
            select(Device).where(Device.uid == UUID(device_id), Device.owner == user_id)
        ).first()
        if not device:
            await ws.close(code=4004, reason="Device not found")
            return
    finally:
        session.close()

    await manager.connect_device(user_id, device_id, ws)

    # Broadcast device online
    online_msg = {"uid": device_id}
    await manager.send_to_user(user_id, {
        "type": "event", "event": "device_online", "data": online_msg
    })
    await manager.send_to_user_device(user_id, {
        "type": "event", "event": "device_online", "data": online_msg
    })

    try:
        while True:
            data = await ws.receive_json()
            action = data.get('action')

            if action == 'toggle_status':
                session = next(get_session())
                try:
                    device = session.exec(
                        select(Device).where(Device.uid == UUID(device_id), Device.owner == user_id)
                    ).first()
                    if not device:
                        await ws.send_json({"type": "error", "msg": "Device not found"})
                        continue

                    device.is_active = not device.is_active
                    session.add(device)
                    session.commit()
                    session.refresh(device)

                    new_status = device.is_active
                    await ws.send_json({
                        "type": "response",
                        "action": "toggle_status",
                        "data": {"device_status": new_status}
                    })
                    status_msg = {"uid": device_id, "is_active": new_status}
                    await manager.send_to_user(user_id, {
                        "type": "event", "event": "device_status_change", "data": status_msg
                    })
                    await manager.send_to_user_device(user_id, {
                        "type": "event", "event": "device_status_change", "data": status_msg
                    })
                finally:
                    session.close()

            elif action == 'refresh':
                session = next(get_session())
                try:
                    device = session.exec(
                        select(Device).where(Device.uid == UUID(device_id), Device.owner == user_id)
                    ).first()
                    if not device:
                        await ws.send_json({"type": "error", "msg": "Device not found"})
                        continue

                    from app.models import get_user_devices
                    all_devices = get_user_devices(user_id, session)
                    devices_data = []
                    for d in all_devices:
                        devices_data.append({
                            "uid": str(d.uid),
                            "name": d.name,
                            "type": d.type,
                            "ip": d.ip,
                            "is_active": d.is_active,
                        })

                    await ws.send_json({
                        "type": "response",
                        "action": "refresh",
                        "data": {
                            "device": {
                                "uid": str(device.uid),
                                "name": device.name,
                                "type": device.type,
                                "ip": device.ip,
                                "is_active": device.is_active,
                            },
                            "all_devices": devices_data,
                        }
                    })
                finally:
                    session.close()

            elif action == 'send_message':
                text = data.get('data', {}).get('text', '')
                target_device = data.get('data', {}).get('target_device')
                if text:
                    msg_payload = {"from_device": device_id, "message": text}
                    await manager.send_to_user(user_id, {
                        "type": "event", "event": "device_message", "data": msg_payload
                    })
                    if target_device and target_device != device_id and manager.is_device_connected(target_device):
                        await manager.send_to_device(target_device, {
                            "type": "event", "event": "device_message", "data": msg_payload
                        })
                    else:
                        await manager.send_to_user_device(user_id, {
                            "type": "event", "event": "device_message", "data": msg_payload
                        })

            elif action == 'terminal_exec':
                command = data.get('data', {}).get('command', '')
                target_device = data.get('data', {}).get('target_device')
                if command:
                    output_payload = {
                        "from_device": device_id,
                        "command": command,
                        "output": f"Command received: {command}",
                        "exit_code": 0,
                    }
                    if target_device and target_device != device_id and manager.is_device_connected(target_device):
                        await manager.send_to_device(target_device, {
                            "type": "event", "event": "cmd_output", "data": output_payload
                        })
                    else:
                        await manager.send_to_user_device(user_id, {
                            "type": "event", "event": "cmd_output", "data": output_payload
                        })

            elif action == 'clipboard_sync':
                text = data.get('data', {}).get('text', '')
                if text:
                    await manager.send_to_user_device_except(user_id, device_id, {
                        "type": "event",
                        "event": "clipboard_sync",
                        "data": {
                            "text": text,
                            "source_device": device_id,
                            "timestamp": str(datetime.now(timezone.utc)),
                        },
                    })

            elif action == 'get_devices':
                session = next(get_session())
                try:
                    from app.models import get_user_devices
                    all_devices = get_user_devices(user_id, session)
                    connected_ids = manager.get_user_connected_devices(user_id)
                    devices_data = []
                    for d in all_devices:
                        devices_data.append({
                            "uid": str(d.uid),
                            "name": d.name,
                            "type": d.type,
                            "ip": d.ip,
                            "is_active": d.is_active,
                            "is_online": str(d.uid) in connected_ids,
                        })
                    await ws.send_json({
                        "type": "response",
                        "action": "get_devices",
                        "data": {"devices": devices_data}
                    })
                finally:
                    session.close()

            elif action == 'rename_device':
                params = data.get('data', {})
                device_uid = params.get('device_uid')
                new_name = params.get('new_name')
                if not device_uid or not new_name:
                    await ws.send_json({"type": "error", "msg": "Missing device_uid or new_name"})
                    continue
                session = next(get_session())
                try:
                    device = get_device_db(device_uid, user_id, session)
                    if not device:
                        await ws.send_json({"type": "error", "msg": "Device not found"})
                        continue
                    device.name = new_name
                    stats, _ = update_device(device, session)
                    if stats == 200:
                        renamed_msg = {"uid": device_uid, "name": new_name}
                        await ws.send_json({
                            "type": "response",
                            "action": "rename_device",
                            "data": {"uid": device_uid, "name": new_name}
                        })
                        await manager.send_to_user(user_id, {
                            "type": "event", "event": "device_renamed", "data": renamed_msg
                        })
                        await manager.send_to_user_device(user_id, {
                            "type": "event", "event": "device_renamed", "data": renamed_msg
                        })
                    else:
                        await ws.send_json({"type": "error", "msg": "Failed to rename device"})
                finally:
                    session.close()

    except WebSocketDisconnect:
        manager.disconnect_device(device_id)
        offline_msg = {"uid": device_id}
        await manager.send_to_user(user_id, {
            "type": "event", "event": "device_offline", "data": offline_msg
        })
        await manager.send_to_user_device(user_id, {
            "type": "event", "event": "device_offline", "data": offline_msg
        })
    except Exception:
        manager.disconnect_device(device_id)
        offline_msg = {"uid": device_id}
        await manager.send_to_user(user_id, {
            "type": "event", "event": "device_offline", "data": offline_msg
        })
        await manager.send_to_user_device(user_id, {
            "type": "event", "event": "device_offline", "data": offline_msg
        })
