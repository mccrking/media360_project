FROM apache/airflow:2.10.2-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
USER airflow

RUN pip install --no-cache-dir --no-deps apache-airflow-providers-fab==1.3.0 && pip install --no-cache-dir minio feedparser beautifulsoup4 requests pyyaml
