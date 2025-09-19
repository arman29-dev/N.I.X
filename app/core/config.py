from fastapi import Request
from fastapi.templating import Jinja2Templates

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from dotenv import load_dotenv
from logging import getLogger
from pathlib import Path
from os.path import join
from os import getenv



limiter = Limiter(key_func=get_remote_address)
security_logger = getLogger("security")

ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(join(ROOT_DIR, '.env'))

static_dir = ROOT_DIR / "static"
template_dir = ROOT_DIR / "templates"
templates = Jinja2Templates(directory=template_dir)

AUTH_QRCODE_ROOT_DIR = static_dir / "auth-QRs"
DEVICE_QRCODE_ROOT_DIR = static_dir / "device-QRs"
LOG_DIR = ROOT_DIR / "logs"

SENDER = str(getenv('EMAIL_HOST'))
SECRET_KEY = str(getenv('SECRET_KEY'))
SENDER_PASSWORD = str(getenv('EMAIL_HOST_PASSWORD'))


def rate_limit_handler(req: Request, exc: RateLimitExceeded):
    client_ip = req.client.host if req.client else 'unknown'
    security_logger.warning(f"Rate limit exceeded for: {req.method} {req.url} from IP: {client_ip}")

    return _rate_limit_exceeded_handler(req, exc)
