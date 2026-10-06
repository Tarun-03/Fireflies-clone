import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings


def test_configuration_rejects_weak_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(internal_api_token="short")


def test_live() -> None:
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
