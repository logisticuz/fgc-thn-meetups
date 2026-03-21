import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from src.routers import admin, kiosk, reports


@pytest.fixture()
def app():
    test_app = FastAPI(title="FGC THN Meetups Test")
    test_app.add_middleware(SessionMiddleware, secret_key="test-secret")
    test_app.include_router(kiosk.router)
    test_app.include_router(admin.router)
    test_app.include_router(reports.router)
    return test_app


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_client(client):
    response = client.post("/admin/login", data={"pin": "fgcthn2016"}, follow_redirects=False)
    assert response.status_code == 302
    return client
