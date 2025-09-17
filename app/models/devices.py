from sqlmodel import Field, SQLModel
import uuid


class Device(SQLModel, table=True):
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str|None = Field(default=None, max_length=100, nullable=True)
    type: str = Field(default="unknown", max_length=50)

    is_active: bool = Field(default=True)
    is_revoked: bool = Field(default=False)

    owner: str = Field(foreign_key="user.uid")
    access_token: str = Field(default_factory=lambda: str(uuid.uuid4()), max_length=256)
