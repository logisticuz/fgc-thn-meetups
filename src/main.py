from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from .config import settings
from . import db  # noqa: F401
from .routers import kiosk, admin, reports


class AuthGateMiddleware:
    """Pure ASGI middleware — redirects unauthenticated requests to /login."""

    EXEMPT_PREFIXES = ("/login", "/static")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope["path"]
        if any(path == p or path.startswith(p + "/") for p in self.EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        session = scope.get("session", {})
        if not session.get("authenticated"):
            if path.startswith("/api/"):
                response = JSONResponse({"status": "unauthorized"}, status_code=401)
            else:
                response = RedirectResponse("/login")
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


app = FastAPI(title="FGC THN Meetups")
# SessionMiddleware added last → outermost (decodes cookie first).
# AuthGateMiddleware added first → inner (session already available).
app.add_middleware(AuthGateMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(kiosk.router)
app.include_router(admin.router)
app.include_router(reports.router)
