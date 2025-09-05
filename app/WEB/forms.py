from pydantic import BaseModel


class loginFormModel(BaseModel):
    email: str
    password: str


class registerFormModel(BaseModel):
    email: str
    username: str
    password: str
    cnfmPassword: str
