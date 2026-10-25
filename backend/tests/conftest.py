import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from config import Config  # noqa: E402


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        import seed
        seed.seed()
        yield app
        db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def login(client):
    def _login(email, password):
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.json
        return {"Authorization": "Bearer " + r.json["token"]}
    return _login
