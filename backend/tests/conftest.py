import os

os.environ["INTERNAL_API_TOKEN"] = "test-only-service-token-with-32-characters"
os.environ["ENVIRONMENT"] = "test"

import pytest


@pytest.fixture(autouse=True)
def provider_cooldown_reset():
    from app.services.provider_guard import record_result

    record_result(True)
    yield
    record_result(True)
