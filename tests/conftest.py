import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from src import crud
from src.main import AuthGateMiddleware
from src.routers import admin, kiosk, reports


@pytest.fixture()
def app():
    test_app = FastAPI(title="FGC THN Meetups Test")
    test_app.add_middleware(AuthGateMiddleware)
    test_app.add_middleware(SessionMiddleware, secret_key="test-secret")
    test_app.include_router(kiosk.router)
    test_app.include_router(admin.router)
    test_app.include_router(reports.router)
    return test_app


@pytest.fixture()
def unauthenticated_client(app):
    """Client without any login — blocked by AuthGateMiddleware."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def client(app):
    """Authenticated client (logged in via PIN)."""
    with TestClient(app) as test_client:
        with patch.object(crud, "log_action"):
            resp = test_client.post("/login", data={"pin": "fgcthn2016"}, follow_redirects=False)
            assert resp.status_code == 302
        yield test_client


@pytest.fixture()
def admin_client(client):
    """Alias — login already sets is_admin."""
    return client
