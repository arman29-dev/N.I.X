from pydantic import BaseModel, Field, EmailStr


class apiLoginForm(BaseModel):
    email: EmailStr
    password: str
    twoFA: str


class deviceForm(BaseModel):
    uid: str
    name: str
    type: str
    ip: str
    owner: str
    token_ID: str


class deleteDeviceForm(BaseModel):
    device_uid: str
    access_token_uid: str


class loginForm(BaseModel):
    email: EmailStr
    password: str


class registerForm(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=8, max_length=128)
    cnfmPassword: str


class passwordResetForm(BaseModel):
    new_pswd: str = Field(min_length=8, max_length=128)
    cnfm_pswd: str
    verification_code: int
    verification_code_hash: str = ""
