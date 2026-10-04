FROM python:3.12-slim

WORKDIR /code
RUN apt-get update -y && apt-get install -y cron logrotate git procps
COPY requirements.lock requirements-vcs.txt ./
# Save Docker container disk space since the cache is useless there
# and don't generate .pyc.  The lock contains the complete production graph,
# including the process entrypoints, so pip does not resolve newer packages.
RUN pip install --no-deps -r requirements-vcs.txt --no-compile --no-cache-dir \
    && pip install --require-hashes --no-deps -r requirements.lock --no-compile --no-cache-dir
COPY . .
ARG CRCON_VERSION=unknown
# Immutable image metadata wins over stale compose environment variables.
RUN printf '%s\n' "$CRCON_VERSION" > /code/release_version
ENV PYTHONPATH=/code/
RUN chmod +x entrypoint.sh
RUN chmod +x manage.py
RUN chmod +x rconweb/manage.py
ENV LOGGING_FILENAME=startup.log

ENTRYPOINT [ "/code/entrypoint.sh" ]
