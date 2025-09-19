from pydantic import BaseModel, EmailStr


class loginForm(BaseModel):
    email: EmailStr
    password: str
    twoFA: int


class deviceForm(BaseModel):
    uid: str
    name: str
    type: str
    ip: str
    port: int|None
    owner: str
