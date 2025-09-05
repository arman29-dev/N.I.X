from fastapi.templating import Jinja2Templates

from pathlib import Path
from secrets import token_urlsafe


static_dir = Path(__file__).parent.parent.parent / "static"
template_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=template_dir)

SECRET_KEY = token_urlsafe(32)
