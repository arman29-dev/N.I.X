from pydantic import BaseModel, EmailStr


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
