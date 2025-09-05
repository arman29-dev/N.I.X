from fastapi import APIRouter


webApp = APIRouter(
    prefix="/web",
    tags=[
        "Web", "WebApp",
        "N.I.X-Dashboard"
    ],
)
