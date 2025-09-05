from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    uid: str = Field(default="xxxxx-xxx-xxx-xxxxx", unique=True)
    email: str = Field(primary_key=True)
    username: str
    password: str
