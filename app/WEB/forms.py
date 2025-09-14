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


class passwordResetForm(BaseModel):
    new_pswd: str
    cnfm_pswd: str
    verification_code: int
    verification_code_hash: str
