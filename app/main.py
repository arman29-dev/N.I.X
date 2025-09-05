from fastapi import FastAPI
from sqlmodel import SQLModel
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .core.config import static_dir, SECRET_KEY
from .API.routes.user import user
from .WEB.pages import webApp
from .models import engine



app = FastAPI(title="N.I.X Project")

# Initialize database
SQLModel.metadata.create_all(engine)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize session middleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.include_router(user)
app.include_router(webApp)
