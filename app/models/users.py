from sqlmodel import Field, SQLModel
from datetime import datetime


class User(SQLModel, table=True):
    uid: str = Field(default="xxxxx-xxx-xxx-xxxxx", unique=True)
    email: str = Field(primary_key=True)
    username: str
    password: str = Field(min_length=8, max_length=128)

    verification_code: str|None = Field(default='000000', max_length=6, nullable=True)
    code_expires_at: datetime|None = Field(default=datetime.now(), nullable=True)

    twoFA_secret: str|None = Field(max_length=32, nullable=True)
    qr_code_path: str|None = Field(max_length=255, default="", nullable=True)
