from fastapi.templating import Jinja2Templates

from secrets import token_urlsafe
from dotenv import load_dotenv
from pathlib import Path
from os.path import join
from os import getenv


ROOT_DIR = Path(__file__).parent.parent.parent

static_dir = ROOT_DIR / "static"
template_dir = ROOT_DIR / "templates"
templates = Jinja2Templates(directory=template_dir)

SECRET_KEY = token_urlsafe(32)

AUTH_QRCODE_ROOT_DIR = static_dir / "auth-QRs"


load_dotenv(join(ROOT_DIR, '.env'))

SENDER = str(getenv('EMAIL_HOST'))
SENDER_PASSWORD = str(getenv('EMAIL_HOST_PASSWORD'))
