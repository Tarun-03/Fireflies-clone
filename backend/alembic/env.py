from alembic import context
from app.core.config import get_settings
from app.db.engine import make_engine
from app.models import metadata

if context.is_offline_mode():
    context.configure(url=get_settings().database_url, target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(get_settings().database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
