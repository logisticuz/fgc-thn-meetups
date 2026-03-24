"""PIN login lockout — in-memory rate limiting."""

from collections import defaultdict
from time import time

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 900  # 15 minutes

_attempts: dict[str, list[float]] = defaultdict(list)


def _clean(ip: str) -> None:
    now = time()
    _attempts[ip] = [t for t in _attempts[ip] if now - t < LOCKOUT_SECONDS]


def is_locked_out(ip: str) -> bool:
    _clean(ip)
    return len(_attempts[ip]) >= MAX_ATTEMPTS


def remaining_lockout_seconds(ip: str) -> int:
    if not _attempts[ip]:
        return 0
    oldest = _attempts[ip][-MAX_ATTEMPTS] if len(_attempts[ip]) >= MAX_ATTEMPTS else _attempts[ip][0]
    remaining = LOCKOUT_SECONDS - (time() - oldest)
    return max(0, int(remaining))


def record_failed_attempt(ip: str) -> None:
    _attempts[ip].append(time())


def clear_attempts(ip: str) -> None:
    _attempts.pop(ip, None)


def failed_count(ip: str) -> int:
    _clean(ip)
    return len(_attempts[ip])


def get_client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"
