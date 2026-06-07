from datetime import datetime
from sqlmodel import Field, SQLModel


class CommandRequest(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.uid", index=True)
    name: str = Field(max_length=100)
    description: str = Field(max_length=1000)
    status: str = Field(default="pending", max_length=20)
    created_at: datetime = Field(default=datetime.now())
