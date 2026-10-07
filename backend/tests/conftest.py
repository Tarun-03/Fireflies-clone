import os

os.environ["INTERNAL_API_TOKEN"] = "test-only-service-token-with-32-characters"
os.environ["ENVIRONMENT"] = "test"
# Tests always use disposable local files, even if the operator has cloud credentials.
os.environ["TURSO_DATABASE_URL"] = ""
os.environ["TURSO_AUTH_TOKEN"] = ""

import pytest


@pytest.fixture(autouse=True)
def provider_cooldown_reset():
    from app.services.provider_guard import record_result

    record_result(True)
    yield
    record_result(True)


def pytest_addoption(parser):
    parser.addoption(
        "--libsql", action="store_true", help="Run DB integration tests on real local libSQL"
    )
