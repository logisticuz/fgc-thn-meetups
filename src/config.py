from dataclasses import dataclass
import os
import warnings

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

_WEAK_DEFAULTS = {"fgcthn2016", "change-me", ""}


@dataclass(frozen=True)
class Settings:
    admin_pin: str = os.getenv("ADMIN_PIN", "fgcthn2016")
    dev_pin: str = os.getenv("DEV_PIN", "")
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://fgc:devpassword@postgres:5432/fgc_checkin",
    )
    n8n_url: str = os.getenv("N8N_URL", "http://n8n:5678")

    def __post_init__(self):
        if self.admin_pin in _WEAK_DEFAULTS:
            warnings.warn("ADMIN_PIN is using a weak default — set a strong value in .env", stacklevel=2)
        if self.secret_key in _WEAK_DEFAULTS:
            warnings.warn("SECRET_KEY is using a weak default — set a strong value in .env", stacklevel=2)


settings = Settings()
