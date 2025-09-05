from fastapi import Request, Form
from starlette.status import HTTP_302_FOUND
from fastapi.responses import HTMLResponse, RedirectResponse

from app.models import SessionDep, User, get_user, register_user
from app.core.config import templates

from . import webApp
from .forms import loginFormModel, registerFormModel

from passlib.hash import pbkdf2_sha256 as secure_password
from typing import Annotated
from uuid import uuid4



# Root Route
@webApp.get("/", response_class=HTMLResponse)
async def root(req: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": req}
    )


# Home Route
@webApp.get("/home", response_class=HTMLResponse)
async def home(req: Request):
    return templates.TemplateResponse(
        "home.html",
        {"request": req}
    )

# Login Route
@webApp.post("/login/")
async def login(req: Request, data: Annotated[loginFormModel, Form()], session: SessionDep):
    user = get_user(data.email, session)
    if user is None:
        return templates.TemplateResponse(
            "home.html",
            {
                "request": req,
                "error": "Invalid email"
            }
        )

    if not secure_password.verify(data.password, user.password):
        return templates.TemplateResponse(
            "home.html",
            {
                "request": req,
                "error": "Invalid email or password"
            }
        )

    req.session[data.email] = user.uid
    return RedirectResponse("/web/test", status_code=HTTP_302_FOUND)

# Register Route
@webApp.post("/register/")
async def register(req: Request, data: Annotated[registerFormModel, Form()], session: SessionDep):
    user = User(
        uid=str(uuid4()),
        email=data.email,
        username=data.username,
        password=secure_password.hash(data.password)
    )

    status, msg = register_user(user, session)
    if status == 200:
        return RedirectResponse("/web/test", status_code=HTTP_302_FOUND)

    elif status == 500:
        return templates.TemplateResponse(
            "home.html",
            {
                "request": req,
                "error": msg
            }
        )
