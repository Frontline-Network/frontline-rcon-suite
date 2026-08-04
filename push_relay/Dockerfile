FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
RUN useradd --create-home relay && mkdir -p /data && chown relay:relay /data
USER relay
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
