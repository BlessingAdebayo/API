import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from main import app
from mm.api.container import FakeContainer, di_container
from mm.api.routes import avatea
from mm.api.security import verify_token


class AppTest:
    def __init__(self, app: FastAPI, client: TestClient, container: FakeContainer):
        self.app = app
        self.client = client
        self.container = container


@pytest.fixture
def mm_app_unit():
    fake_container = FakeContainer()

    avatea.dependency_overrides[di_container] = lambda: fake_container
    avatea.dependency_overrides[verify_token] = lambda: None  # Disables authentication.

    client = TestClient(app)

    return AppTest(app=app, client=client, container=fake_container)
