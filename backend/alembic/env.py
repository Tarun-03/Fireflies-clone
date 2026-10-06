from typing import Any

from alembic import context
from app.core.config import get_settings
from app.db.engine import make_engine
from app.models import metadata


def include_object(obj: Any, name: str | None, kind: str, reflected: bool, compare_to: Any) -> bool:
    # FTS virtual/shadow tables are managed explicitly by the search migration.
    return not (
        kind == "table"
        and name
        in {
            "search_documents_fts",
            "search_documents_fts_data",
            "search_documents_fts_idx",
            "search_documents_fts_docsize",
            "search_documents_fts_config",
        }
    )


if context.is_offline_mode():
    context.configure(url=get_settings().database_url, target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(get_settings().database_url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=metadata,
            render_as_batch=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()
