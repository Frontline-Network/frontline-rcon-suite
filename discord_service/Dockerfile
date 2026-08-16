ARG CODEX_VERSION=0.146.0
FROM node:22-bookworm-slim AS codex
ARG CODEX_VERSION
RUN npm install --global "@openai/codex@${CODEX_VERSION}"

FROM python:3.13-slim-bookworm

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY --from=codex /usr/local/bin/node /usr/local/bin/node
COPY --from=codex /usr/local/lib/node_modules/@openai/codex /usr/local/lib/node_modules/@openai/codex
RUN ln -s /usr/local/lib/node_modules/@openai/codex/bin/codex.js /usr/local/bin/codex
RUN pip install --no-cache-dir .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
