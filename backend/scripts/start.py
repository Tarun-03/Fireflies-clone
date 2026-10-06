"""Prepare the mounted database and validate fixtures before accepting requests."""

import os
from pathlib import Path

import uvicorn
from alembic.config import Config

from alembic import command
from app.core.config import get_settings
from app.services.seed import SeedTemplate


def prepare() -> None:
    root = Path(__file__).resolve().parents[1]
    settings = get_settings()
    database = Path(settings.database_url.removeprefix("sqlite:///")).resolve()
    if not database.parent.is_dir():
        raise RuntimeError("The database directory is missing. Mount the persistent volume first.")
    if settings.environment == "production" and database.parent != Path("/var/data"):
        raise RuntimeError("Production SQLite must use the mounted /var/data directory.")
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(config, "head")
    template = SeedTemplate.model_validate_json((root / "fixtures" / "seed-v1.json").read_bytes())
    if template.schema_version != 1 or len(template.meetings) < 8:
        raise RuntimeError("The synthetic meeting template is incomplete.")
    # Validate the template; actual cloning occurs once per visitor, never on restart.
    print("Database ready; synthetic template validated.", flush=True)


def main() -> None:
    prepare()
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("BIND_HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        workers=1,
        limit_concurrency=32,
        backlog=64,
        timeout_keep_alive=5,
        timeout_graceful_shutdown=35,
        proxy_headers=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()
