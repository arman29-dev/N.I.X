from pydantic import BaseModel, EmailStr


class loginForm(BaseModel):
    email: EmailStr
    password: str
    twoFA: int
