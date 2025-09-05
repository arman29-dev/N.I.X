from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    uid: str = Field(default="xxxxx-xxx-xxx-xxxxx", unique=True)
    email: str = Field(primary_key=True)
    username: str
    password: str

    twoFA_secret: str|None = Field(max_length=32, nullable=True)
    qr_code_path: str|None = Field(max_length=255, default="", nullable=True)
