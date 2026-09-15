FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml ./
COPY darkbloom_metrics/ darkbloom_metrics/
RUN pip install .

RUN useradd -r -u 1000 metrics
USER metrics

ENTRYPOINT ["darkbloom-metrics-client"]
