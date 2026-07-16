from fastapi import APIRouter, WebSocket
from fastapi.encoders import jsonable_encoder

from app.core.auth import verify2FAcode

from app.models import SessionDep
from app.models.users import User

from typing import Literal
from passlib.hash import pbkdf2_sha256 as password
from logging import getLogger



logger = getLogger(__name__)


deviceApi = APIRouter(
    prefix="/api/v1/device",
    tags=["Device API"],
)

userApi = APIRouter(
    prefix="/api/v1/user",
    tags=["User API"],
)

commsWS = APIRouter(
    prefix="/comms",
    tags=["Communication API"],
)

logApi = APIRouter(
    prefix="/api/v1",
    tags=["Logs API"],
)

cmdRequestApi = APIRouter(
    prefix="/api/v1",
    tags=["Command Requests API"],
)


def login(user: User, session: SessionDep, **credentials) -> tuple[Literal[200, 401], dict]:
    if not password.verify(credentials['password'], user.password):
        return 401, {'Error': 'Invalid password'}

    if not verify2FAcode(user.uid, str(credentials['twoFA']), session):
        return 401, {'Error': 'Invalid 2FA code'}

    return 200, {'success': True}


class WSConnectionManager:
    def __init__(self):
        self.user_connections: dict[str, list[WebSocket]] = {}
        self.device_connections: dict[str, WebSocket] = {}
        self.device_to_user: dict[str, str] = {}

    async def connect_user(self, user_id: str, ws: WebSocket):
        await ws.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(ws)
        logger.info(f"User WS connected: {user_id} (total: {len(self.user_connections[user_id])})")

    async def connect_device(self, user_id: str, device_id: str, ws: WebSocket):
        await ws.accept()
        self.device_connections[device_id] = ws
        self.device_to_user[device_id] = user_id
        logger.info(f"Device WS connected: {device_id} for user {user_id}")

    def disconnect_user(self, user_id: str, ws: WebSocket):
        connections = self.user_connections.get(user_id, [])
        if ws in connections:
            connections.remove(ws)
            logger.info(f"User WS disconnected: {user_id} (remaining: {len(connections)})")

    async def disconnect_device(self, device_id: str):
        ws = self.device_connections.pop(device_id, None)
        self.device_to_user.pop(device_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
        logger.info(f"Device WS disconnected: {device_id}")

    async def send_to_user(self, user_id: str, message: dict):
        connections = self.user_connections.get(user_id, [])
        if not connections:
            logger.warning(f"send_to_user: no WS connections for user {user_id}")
            return
        payload = jsonable_encoder(message)
        stale = []
        for ws in connections:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect_user(user_id, ws)

    async def send_to_device(self, device_id: str, message: dict):
        ws = self.device_connections.get(device_id)
        if not ws:
            logger.warning(f"Device {device_id} not connected")
            return
        try:
            await ws.send_json(jsonable_encoder(message))
        except Exception:
            await self.disconnect_device(device_id)

    async def broadcast_to_user(self, user_id: str, message: dict):
        await self.send_to_user(user_id, message)

    async def send_to_user_device(self, user_id: str, message: dict):
        for device_id, ws in self.device_connections.items():
            if self.device_to_user.get(device_id) == user_id:
                try:
                    await ws.send_json(jsonable_encoder(message))
                except Exception:
                    await self.disconnect_device(device_id)

    async def send_to_user_device_except(self, user_id: str, exclude_device_id: str, message: dict):
        for device_id, ws in self.device_connections.items():
            if device_id == exclude_device_id:
                continue
            if self.device_to_user.get(device_id) == user_id:
                try:
                    await ws.send_json(jsonable_encoder(message))
                except Exception:
                    await self.disconnect_device(device_id)

    def get_user_for_device(self, device_id: str) -> str | None:
        return self.device_to_user.get(device_id)

    def is_device_connected(self, device_id: str) -> bool:
        return device_id in self.device_connections

    def get_user_connected_devices(self, user_id: str) -> list[str]:
        return [did for did, uid in self.device_to_user.items() if uid == user_id]
