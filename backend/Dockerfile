FROM ghcr.io/astral-sh/uv:0.12.23 AS uv
FROM python:3.13.5-slim
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY fixtures ./fixtures
COPY assets ./assets
COPY scripts ./scripts
RUN useradd --uid 10001 --create-home workspace
USER workspace
# Local Compose only; remote deployment never opens this directory.
RUN mkdir /home/workspace/data
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
CMD ["python", "-m", "scripts.start"]
