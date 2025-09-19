from jwt import encode, decode, ExpiredSignatureError, InvalidTokenError

from app.core.config import SECRET_KEY, JWT_HASH_ALGORITHM

from datetime import datetime, timedelta



def generate_token(data: dict, expires_delta: timedelta = timedelta(days=30)) -> str:
    to_encode = data.copy()
    expire = datetime.now() + expires_delta

    to_encode.update({"exp": expire})

    token = encode(to_encode, SECRET_KEY, algorithm=JWT_HASH_ALGORITHM)
    return token


def verify_token(token: str) -> dict | None:
    try:
        payload = decode(token, SECRET_KEY, algorithms=[JWT_HASH_ALGORITHM])
        return payload
    except (ExpiredSignatureError, InvalidTokenError):
        return None
