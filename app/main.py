from sqlmodel import SQLModel
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse

from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from slowapi.errors import RateLimitExceeded

from .core.config import static_dir, limiter, rate_limit_handler, SECRET_KEY, templates
from .core.middleware import RequestLoggingMiddleware
from .core.sLogger import logger
from .models import engine

from .web.pages import webApp
from .api.device import deviceApi
from .api.user import userApi
from .api.comms import commsWS
from .api.logs import logApi
from .api.cmd_requests import cmdRequestApi

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up N.I.X")
    yield
    # Shutdown
    logger.info("Shutting down N.I.X")


app = FastAPI(title="N.I.X Project", lifespan=lifespan)

# Initialize database
SQLModel.metadata.create_all(engine)


# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")


app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[
    "localhost", "127.0.0.1", "0.0.0.0", 
    "quiet-pup-summary.ngrok-free.app"
])

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


# Initialize rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # type: ignore


#Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(req: Request, exc: Exception):
    logger.error(
        f"Unhandled exception on {req.method} {req.url}: {exc}",
        exc_info=True, extra={
            'method': req.method,
            'url': str(req.url),
            'client_ip': req.client.host if req.client else 'unknown'
        }
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )


@app.get('/')
async def redirect_to_root(req: Request):
    return templates.TemplateResponse("index.html", {"request": req})

@app.get('/ping')
def server_status():
    return JSONResponse({'status': 'Online'}, status_code=200)


# Include/Registering routers
app.include_router(deviceApi)
app.include_router(userApi)
app.include_router(commsWS)
app.include_router(logApi)
app.include_router(cmdRequestApi)
app.include_router(webApp)
