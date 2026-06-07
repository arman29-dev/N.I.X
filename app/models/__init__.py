from fastapi import Depends
from sqlmodel import Session, select, create_engine

from typing import Annotated, Literal
from logging import getLogger
from uuid import UUID

from .users import User, Token
from .devices import Device
from .command_request import CommandRequest


logger = getLogger(__name__)
engine = create_engine("sqlite:///Database/database.db")

def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

def register_user(user: User, session: SessionDep) -> tuple[Literal[200, 500], str]:
    try:
        session.add(user)
        session.commit()
        session.refresh(user)
        return 200, "Successfully Registered"

    except Exception as E:
        session.rollback()
        return 500, str(E)


def delete_user(uid: str, session: SessionDep) -> tuple[Literal[200, 404, 500], str]:
    try:
        # Delete all user devices
        devices_statement = select(Device).where(Device.owner == uid)
        devices = session.exec(devices_statement).all()
        for device in devices:
            session.delete(device)

        # Delete all user tokens
        tokens_statement = select(Token).where(Token.owner == uid)
        tokens = session.exec(tokens_statement).all()
        for token in tokens:
            session.delete(token)

        # Delete user
        user_statement = select(User).where(User.uid == uid)
        user = session.exec(user_statement).first()
        if not user:
            return 404, "User not found"

        session.delete(user)
        session.commit()
        return 200, "User and all associated data deleted successfully"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while deleting user {uid}: {E}", exc_info=True)
        return 500, str(E)


def get_user(email: str, session: SessionDep) -> User|None:
    try:
        statement = select(User).where(User.email == email)
        user = session.exec(statement).first()
        return user
    except Exception as E:
        logger.error(f"Database error while fetching user {email}: {E}", exc_info=True)
        raise


def get_user_by_id(uid: str, session: SessionDep) -> User|None:
    try:
        statement = select(User).where(User.uid == uid)
        user = session.exec(statement).first()
        return user

    except Exception as E:
        logger.error(f"Database error while fetching user by ID {uid}: {E}", exc_info=True)
        raise


def get_user_access_token(uid: str, session: SessionDep) -> tuple[str, str]|None:
    try:
        statement = select(Token).where(Token.owner == uid)
        token = session.exec(statement).first()
        if token:
            return token.access_token, str(token.uid)
        return None

    except Exception as E:
        logger.error(f"Database error while fetching access token for user {uid}: {E}", exc_info=True)
        raise

def register_token(token: Token, session: SessionDep) -> tuple[Literal[200, 500], str]:
    try:
        session.add(token)
        session.commit()
        session.refresh(token)
        return 200, "Token successfully registered"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while registering token for user {token.owner}: {E}", exc_info=True)
        return 500, str(E)


def update_user(user: User, session: SessionDep) -> tuple[Literal[200, 500], str]:
    try:
        session.add(user)
        session.commit()
        session.refresh(user)
        return 200, "Successfully Updated"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while updating user {user.email}: {E}", exc_info=True)
        return 500, str(E)


def get_user_devices(owner_uid: str, session: SessionDep) -> list[Device]|None:
    try:
        statement = select(Device).where(Device.owner == owner_uid)
        devices = session.exec(statement).all()
        return list(devices)

    except Exception as E:
        logger.error(f"Database error while fetching devices for owner {owner_uid}: {E}", exc_info=True)
        raise


def update_device(device: Device, session: SessionDep) -> tuple[Literal[200, 500], str]:
    try:
        session.add(device)
        session.commit()
        session.refresh(device)
        return 200, "Device successfully updated"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while updating device {device.uid}: {E}", exc_info=True)
        return 500, str(E)


def register_device(device: Device, session: SessionDep) -> tuple[Literal[200, 500], str]:
    try:
        session.add(device)
        session.commit()
        session.refresh(device)
        return 200, "Device successfully added"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while adding device: {E}", exc_info=True)
        return 500, str(E)


def delete_device(device_uid: str, owner_uid: str, session: SessionDep) -> tuple[Literal[200, 404, 500], str]:
    try:
        device_uuid = UUID(device_uid)
        statement = select(Device).where(Device.uid == device_uuid, Device.owner == owner_uid)
        device = session.exec(statement).first()

        if not device:
            return 404, "Device not found or access denied"

        session.delete(device)
        session.commit()
        return 200, "Device successfully deleted"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while deleting device {device_uid}: {E}", exc_info=True)
        return 500, str(E)


def get_device(device_uid: str, owner_uid: str, session: SessionDep) -> Device|None:
    try:
        statement = select(Device).where(Device.uid == UUID(device_uid), Device.owner == owner_uid)
        device = session.exec(statement).first()
        return device

    except Exception as E:
        logger.error(f"Database error while fetching device {device_uid}: {E}", exc_info=True)
        raise


def delete_token(user_id: str, session: SessionDep) -> tuple[Literal[200, 404, 500], str]:
    try:
        statement = select(Token).where(Token.owner == user_id)
        token = session.exec(statement).first()

        if token is None:
            return 404, "Token not found or access denied"

        session.delete(token)
        session.commit()
        return 200, "Token successfully deleted"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while deleting token: {E}", exc_info=True)
        return 500, str(E)

def delete_device_registered_token(token_uid: str, device_data: Device, session: SessionDep) -> tuple[Literal[200, 404, 500], str]:
    try:
        statement = select(Token).where(
            Token.uid == UUID(token_uid),
            Token.owner == device_data.owner,
            Token.linked_device == str(device_data.uid)
        )
        token = session.exec(statement).first()

        if not token:
            return 404, "Token not found or access denied"

        session.delete(token)
        session.commit()
        return 200, "Device successfully deleted"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while deleting device {device_data.uid}: {E}", exc_info=True)
        return 500, str(E)
