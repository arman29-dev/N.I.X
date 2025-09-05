from fastapi.templating import Jinja2Templates

from pathlib import Path
from secrets import token_urlsafe


ROOT_DIR = Path(__file__).parent.parent.parent

static_dir = ROOT_DIR / "static"
template_dir = ROOT_DIR / "templates"
templates = Jinja2Templates(directory=template_dir)

SECRET_KEY = token_urlsafe(32)

AUTH_QRCODE_ROOT_DIR = static_dir / "auth-QRs"
