import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from main import app
from mm.api.dependencies import Container, di_container
from mm.api.routes import avatea
from mm.api.security import verify_token
from mm.data.repositories import MongoWalletKeyRepository
from mm.domain.repositories import WalletKeyRepository


class AppTest:
    def __init__(self, app: FastAPI, client: TestClient, container: Container):
        self.app = app
        self.client = client
        self.container = container


@pytest.fixture
def mm_app_int():
    container = Container()

    app.dependency_overrides[di_container] = lambda: container
    avatea.dependency_overrides[verify_token] = lambda: None  # Disables authentication.

    client = TestClient(app)

    yield AppTest(app=app, client=client, container=container)

    keys: MongoWalletKeyRepository = container[WalletKeyRepository]
    keys.delete_all()
