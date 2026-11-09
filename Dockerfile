ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE} AS dependencies

WORKDIR /build
# Git is needed only to install the dependency pinned to a full VCS commit.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.lock requirements-vcs.txt ./
RUN pip install --prefix=/install --no-deps -r requirements-vcs.txt --no-compile --no-cache-dir \
    && pip install --prefix=/install --require-hashes --no-deps -r requirements.lock --no-compile --no-cache-dir

FROM ${PYTHON_IMAGE} AS runtime

WORKDIR /code
RUN apt-get update && apt-get install -y --no-install-recommends cron logrotate procps \
    && rm -rf /var/lib/apt/lists/*
COPY --from=dependencies /install/ /usr/local/
# Keep runtime files and release verification assets explicit. The separate
# frontend image still uses its own complete source/assets build context.
COPY rcon/ rcon/
COPY rconweb/ rconweb/
COPY alembic/ alembic/
COPY scripts/ scripts/
COPY docs/releases/ docs/releases/
COPY alembic.ini entrypoint.sh manage.py LICENSE requirements.lock requirements-vcs.txt ./
ARG CRCON_VERSION=unknown
# Immutable image metadata wins over stale compose environment variables.
RUN printf '%s\n' "$CRCON_VERSION" > /code/release_version
ENV PYTHONPATH=/code/
RUN chmod +x entrypoint.sh manage.py rconweb/manage.py
ENV LOGGING_FILENAME=startup.log

ENTRYPOINT [ "/code/entrypoint.sh" ]
