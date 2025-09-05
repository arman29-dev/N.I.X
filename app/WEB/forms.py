from pydantic import BaseModel


class loginForm(BaseModel):
    email: str
    password: str
    twoFA: int


class registerForm(BaseModel):
    email: str
    username: str
    password: str
    cnfmPassword: str


class twoFactorAuthForm(BaseModel):
    verification_code: str
