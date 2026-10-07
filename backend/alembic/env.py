from typing import Any

from alembic import context
from app.db.engine import configured_engine
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


def run(connection: Any) -> None:
    connection.exec_driver_sql("BEGIN IMMEDIATE")
    context.configure(
        transactional_ddl=True,
        connection=connection,
        target_metadata=metadata,
        render_as_batch=True,
        include_object=include_object,
    )
    try:
        with context.begin_transaction():
            context.run_migrations()
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


if context.is_offline_mode():
    context.configure(url="sqlite:///", target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    run(context.config.attributes["connection"])
else:
    engine = configured_engine()
    try:
        with engine.connect() as connection:
            run(connection)
    finally:
        engine.dispose()
