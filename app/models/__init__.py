from fastapi import Depends
from sqlmodel import Session, select, create_engine

from typing import Annotated, Literal
from logging import getLogger

from .users import User, Token
from .devices import Device


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


def get_user(email: str, session: SessionDep) -> User|None:
    try:
        user = session.get(User, {"email": email})
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


def get_user_access_token(uid: str, session: SessionDep) -> str|None:
    try:
        statement = select(Token).where(Token.owner == uid)
        token = session.exec(statement).first()
        if token:
            return token.access_token
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


def get_all_devices(owner_uid: str, session: SessionDep) -> list[Device]|None:
    try:
        statement = select(Device).where(Device.owner == owner_uid)
        devices = session.exec(statement).all()
        return list(devices)

    except Exception as E:
        logger.error(f"Database error while fetching devices for owner {owner_uid}: {E}", exc_info=True)
        raise


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
        statement = select(Device).where(Device.uid == device_uid, Device.owner == owner_uid)
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
        statement = select(Device).where(Device.uid == device_uid, Device.owner == owner_uid)
        device = session.exec(statement).first()
        return device

    except Exception as E:
        logger.error(f"Database error while fetching device {device_uid}: {E}", exc_info=True)
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


def delete_device_registered_token(device_uid: str, session: SessionDep) -> tuple[Literal[200, 404, 500], str]:
    try:
        statement = select(Token).where(Device.uid == device_uid)
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
