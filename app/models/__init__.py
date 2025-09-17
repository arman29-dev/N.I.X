from fastapi import Depends
from sqlmodel import Session, select, create_engine

from typing import Annotated
from logging import getLogger

from .devices import Device
from .users import User


logger = getLogger(__name__)
engine = create_engine("sqlite:///Database/database.db")

def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

def register_user(user: User, session: SessionDep) -> tuple[int, str]:
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


def update_user(user: User, session: SessionDep):
    try:
        session.add(user)
        session.commit()
        session.refresh(user)
        return 200, "Successfully Updated"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while updating user {user.email}: {E}", exc_info=True)
        return 500, str(E)


def get_all_devices(owner_uid: str, session: SessionDep) -> list[Device]:
    try:
        statement = select(Device).where(Device.owner == owner_uid)
        devices = session.exec(statement).all()
        return list(devices)

    except Exception as E:
        logger.error(f"Database error while fetching devices for owner {owner_uid}: {E}", exc_info=True)
        raise


def add_device(device: Device, session: SessionDep) -> tuple[int, str]:
    try:
        session.add(device)
        session.commit()
        session.refresh(device)
        return 200, "Device successfully added"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while adding device: {E}", exc_info=True)
        return 500, str(E)


def delete_device(device_uid: str, owner_uid: str, session: SessionDep) -> tuple[int, str]:
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


def update_device(device: Device, session: SessionDep) -> tuple[int, str]:
    try:
        session.add(device)
        session.commit()
        session.refresh(device)
        return 200, "Device successfully updated"

    except Exception as E:
        session.rollback()
        logger.error(f"Database error while updating device {device.uid}: {E}", exc_info=True)
        return 500, str(E)
