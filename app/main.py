from sqlmodel import SQLModel
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from slowapi.errors import RateLimitExceeded

from .core.config import static_dir, limiter, rate_limit_handler, SECRET_KEY
from .core.middleware import RequestLoggingMiddleware
from .API.routes.user import user
from .core.sLogger import logger
from .WEB.pages import webApp
from .models import engine

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


# Initialize middlewares
app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com"])

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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


# Include/Registering routers
app.include_router(user)
app.include_router(webApp)
