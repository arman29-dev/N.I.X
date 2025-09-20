from sqlmodel import Field, SQLModel
from uuid import UUID


class Device(SQLModel, table=True):
    uid: UUID = Field(primary_key=True)
    name: str|None = Field(default=None, max_length=100, nullable=True)
    type: str = Field(default="unknown", max_length=50)
    ip: str = Field(max_length=45, nullable=False)

    is_active: bool = Field(default=True)
    is_revoked: bool = Field(default=False)

    owner: str = Field(foreign_key="user.uid")
