import unicodedata
from datetime import datetime
from pathlib import Path
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def normalize_header(value: str) -> str:
    value = value.strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace(" ", "_").replace("-", "_")
    return value


def parse_date(value: str | None):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def extract_token(raw: str) -> str | None:
    if not raw:
        return None
    value = raw.strip()
    value = value.split("?")[0].rstrip("/")

    if "//" in value:
        parts = value.split("/")
        return parts[-1] if parts else None

    return value


def is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin"))


def require_admin(request: Request):
    if not is_admin(request):
        return RedirectResponse("/login", status_code=302)
    return None
