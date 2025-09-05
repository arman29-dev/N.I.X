from fastapi import Depends
from sqlmodel import Session, create_engine

from typing import Annotated

from .users import User



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
    user = session.get(User, {"email": email})
    return user
