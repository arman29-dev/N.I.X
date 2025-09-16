from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from re import search



class loginForm(BaseModel):
    email: EmailStr
    password: str
    twoFA: int


class registerForm(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=8, max_length=128)
    cnfmPassword: str

    @field_validator('password')
    def validate_password(cls, v):
        if not search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not search(r'\d', v):
            raise ValueError('Password must contain digit')
        return v

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.cnfmPassword:
            raise ValueError('Passwords do not match')
        return self


class twoFactorAuthForm(BaseModel):
    verification_code: str


class passwordResetForm(BaseModel):
    new_pswd: str = Field(min_length=8, max_length=128)
    cnfm_pswd: str
    verification_code: int
    verification_code_hash: str

    @field_validator('new_pswd')
    def validate_password(cls, v):
        if not search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not search(r'\d', v):
            raise ValueError('Password must contain digit')
        return v

    @model_validator(mode='after')
    def passwords_match(self):
        if self.new_pswd != self.cnfm_pswd:
            raise ValueError('Passwords do not match')
        return self
