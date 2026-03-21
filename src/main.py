from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .config import settings
from . import db  # noqa: F401
from .routers import kiosk, admin, reports

app = FastAPI(title="FGC THN Meetups")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(kiosk.router)
app.include_router(admin.router)
app.include_router(reports.router)
