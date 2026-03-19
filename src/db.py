from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings


def _ensure_sqlite_path(db_url: str) -> None:
    if db_url.startswith("sqlite:///"):
        path = Path(db_url.replace("sqlite:///", ""))
        path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_path(settings.database_url)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
