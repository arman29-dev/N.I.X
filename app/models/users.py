from datetime import datetime, timedelta
from sqlmodel import Field, SQLModel
from uuid import UUID


class User(SQLModel, table=True):
    uid: str = Field(default="xxxxx-xxx-xxx-xxxxx", unique=True)
    email: str = Field(primary_key=True)
    username: str
    password: str = Field(min_length=8, max_length=128)

    verification_code: str|None = Field(default='000000', max_length=6, nullable=True)
    code_expires_at: datetime|None = Field(default=datetime.now(), nullable=True)

    twoFA_secret: str|None = Field(max_length=32, nullable=True)


class Token(SQLModel, table=True):
    uid: UUID = Field(primary_key=True, unique=True)
    owner: str = Field(foreign_key="user.uid")
    access_token: str = Field(max_length=512)
    created_at: datetime = Field(default=datetime.now())
    expires_at: datetime = Field(default=datetime.now() + timedelta(days=30))

    linked_device: str|None = Field(foreign_key="device.uid", default='xxxxx-xxx-xxx-xxxxx', nullable=True)
