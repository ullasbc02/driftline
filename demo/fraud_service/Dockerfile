FROM python:3.11-slim

WORKDIR /app

RUN pip install fastapi uvicorn \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-fastapi

COPY app.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
