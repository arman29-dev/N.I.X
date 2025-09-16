from fastapi import Depends
from sqlmodel import Session, select, create_engine

from typing import Annotated
from logging import getLogger

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
