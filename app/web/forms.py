from pydantic import BaseModel, EmailStr, Field



class loginForm(BaseModel):
    email: EmailStr
    password: str


class registerForm(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=8, max_length=128)
    cnfmPassword: str


class twoFactorAuthForm(BaseModel):
    verification_code: str


class passwordResetForm(BaseModel):
    new_pswd: str = Field(min_length=8, max_length=128)
    cnfm_pswd: str
    verification_code: int
    verification_code_hash: str = ""
