import logging

from .config import settings

logger = logging.getLogger(__name__)

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        import psycopg_pool

        _pool = psycopg_pool.ConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=5,
            open=True,
            kwargs={"autocommit": True},
        )
        logger.info("Postgres connection pool initialized (meetups)")
    return _pool


def get_connection():
    return _get_pool().connection()
