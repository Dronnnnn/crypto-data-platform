FROM apache/airflow:3.3.0-python3.11

USER root

RUN apt-get update \
    && apt-get install --yes --no-install-recommends openjdk-17-jre-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements-airflow.txt .
COPY constraints-airflow.txt .

RUN pip install --no-cache-dir -r requirements-airflow.txt --constraint constraints-airflow.txt
