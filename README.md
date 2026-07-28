# Crypto Data Platform

Cloud-based data engineering project built on AWS.

## Current stack

- AWS S3
- Terraform
- Python
- boto3

## Architecture

Current architecture:

```text
Binance API -> Airflow ingestion -> S3 Raw -> Spark Bronze -> Silver/Gold
```

## Development

Python 3.11
Terraform
AWS CLI

The project uses an S3 data lake with these layers:

- `raw/` is an immutable landing zone for original API JSON.
- `bronze/` will contain validated, typed Parquet produced by Spark.
- `quarantine/` will contain rejected Raw records and the reason for rejection.

Binance Raw objects use Hive-compatible partitions:

```text
raw/source=binance/symbol=BTCUSDT/ingest_date=YYYY-MM-DD/btcusdt_YYYYMMDD_HHMMSS.json
```

The Airflow `binance_ingestion` DAG fetches the API response and writes it straight to
S3 with `ContentType=application/json` and object metadata: source, symbol, ingestion
timestamp, and schema version. It does not write a local JSON file and does not validate
the payload with Pydantic; validation belongs to the Spark Bronze job.

### Terms used in this project

- **Ingestion** is the controlled delivery of data from an external source to the data
  platform. Here it is the Airflow task that requests Binance and writes to S3.
- **Raw / landing zone** is an immutable copy of data as received. It gives the pipeline
  a recoverable source of truth: if a later transformation is wrong, Bronze can be rebuilt
  from Raw.
- **Partitioning** is a directory convention such as `source=binance` and
  `ingest_date=2026-07-27`. Spark, Athena, and dbt can later restrict reads to the
  required partition instead of scanning every object.
- **Bronze** is the first processed layer. The Spark job will parse JSON, cast types,
  deduplicate records, send invalid rows to `quarantine/`, and write Parquet.
- **Quarantine** is an isolated location for invalid records plus the reason they were
  rejected. It preserves evidence without allowing bad data into analytical tables.
