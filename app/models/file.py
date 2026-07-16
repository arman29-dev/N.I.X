from sqlmodel import SQLModel, Field
from uuid import uuid4
from datetime import datetime, timedelta


class FileUpload(SQLModel, table=True):
    id: str       = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    owner_uid: str  = Field(foreign_key="user.uid", index=True, nullable=False)
    file_name: str  = Field(max_length=255, nullable=False)
    file_size: int  = Field(nullable=False)
    mime_type: str  = Field(max_length=127, default="application/octet-stream")
    storage_path: str = Field(max_length=512, nullable=False)
    uploaded_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime  = Field(default_factory=lambda: datetime.now() + timedelta(hours=24))
    downloads: int  = Field(default=0)
