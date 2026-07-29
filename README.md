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
- `silver/` will contain the canonical, consumer-ready crypto-price table.
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

## Local Spark Bronze pipeline

Spark runs as a local **standalone cluster**: `spark-master` coordinates work and
`spark-worker` executes the work. Start it together with Airflow:

```powershell
docker compose --profile spark up -d --build
```

The Spark Master UI is available at `http://localhost:8081`. Triggering
`binance_ingestion` runs three tasks in order: `ingest_raw` lands JSON in Raw,
`raw_to_bronze` creates Bronze Parquet, and `bronze_to_silver` creates Silver Parquet.

The Bronze job reads `s3a://<bucket>/raw/`, which uses Hadoop's S3A connector. It writes
typed Parquet to `bronze/crypto_prices/`, partitioned by `source` and `ingest_date`.
Rows with malformed JSON, a missing or unsupported symbol, a symbol that differs from
the S3 partition, a non-numeric price, or a non-positive price go to
`quarantine/crypto_prices/` with `quarantine_reason` instead of reaching Bronze.

The Silver job reads `bronze/crypto_prices/` and writes
`silver/crypto_prices/`, using the same `source` and `ingest_date` partitions. Silver is
the stable contract for downstream tools: `source`, `symbol`, `price DECIMAL(20,8)`,
`ingest_date`, `bronze_loaded_at`, and `silver_loaded_at`. It does not expose the Raw
file path to consumers. A Bronze record that fails Silver validation is written to
`quarantine/silver_crypto_prices/`.

On its first run Spark downloads the Hadoop AWS connector into its Ivy dependency cache.
The cache is configured under `/tmp/spark-ivy-cache`, a writable temporary directory in
the Airflow container, so a non-root Airflow task can download the JAR files safely.

### Spark transformation tests

The Spark tests validate both transformations. `test_bronze_binance.py` checks valid
Raw rows, invalid prices, duplicate Raw files, and partition/symbol mismatches.
`test_bronze_to_silver.py` checks the Silver contract: valid rows are accepted,
non-positive prices are rejected, duplicates produce one row, and the output schema is
stable. Run them in a disposable Docker container; no local Spark or Java installation is
required:

```powershell
docker compose --profile test run --rm --build spark-tests
```

For a local Python-based test environment, install the optional development dependencies
with `pip install -e ".[dev]"` and then use `pytest -q`.
