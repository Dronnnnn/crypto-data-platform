# Crypto Data Platform

Cloud-based data engineering project built on AWS.

## Current stack

- AWS S3
- Terraform
- Python
- boto3
- Apache Spark
- AWS Glue Data Catalog
- Amazon Athena

## Architecture

Current architecture:

```text
Binance API
  -> Airflow ingestion
  -> S3 Raw (original JSON)
  -> Spark Bronze (validated Parquet)
  -> Spark Silver (canonical Parquet)
  -> Glue Data Catalog
  -> Athena
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
docker compose up -d --build
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

## Glue Data Catalog and Athena

Silver Parquet is the first stable **data contract** in this project. It has agreed
column names and types, invalid records have already been isolated in `quarantine/`, and
the files are partitioned. It is therefore the layer exposed to SQL consumers instead of
the source-specific Raw JSON or technical Bronze records.

The relevant components have different responsibilities:

- **S3** stores the physical JSON and Parquet files.
- **Glue Data Catalog** stores metadata: the logical table name, its schema, the S3
  location, and registered partitions. It does not copy or transform the data.
- **Glue Crawler** can infer a schema from files automatically. It is intentionally not
  used to create the main Silver table: the Terraform definition is the explicit and
  version-controlled schema contract.
- **Glue ETL Job** is AWS-managed Spark. It is not needed here because the local Spark
  jobs already perform Raw-to-Bronze and Bronze-to-Silver transformations.
- **Athena** is a serverless SQL query engine. It uses the Glue table description to read
  the Parquet files directly from S3.

### Silver table and partitions

Terraform creates the Glue database `crypto_data_lake` and the external table
`silver_crypto_prices`. The table points to:

```text
s3://<bucket>/silver/crypto_prices/
```

The following fields are read from each Parquet file:

```text
record_id, symbol, price DECIMAL(20,8), bronze_loaded_at, silver_loaded_at
```

`record_id` is a SHA-256 hash of the landed Raw object path. It is a stable
technical identifier for one source payload: it supports lineage and duplicate checks
without exposing the physical S3 path to consumers.

`source` and `ingest_date` are Glue **partition columns**. Spark writes them as
Hive-style S3 directories:

```text
source=binance/ingest_date=2026-07-29/
```

Athena obtains those two values from the path rather than from a row inside a Parquet
file. In SQL they are used exactly like ordinary columns. Filtering by them enables
**partition pruning**: Athena reads only the required directory instead of scanning every
Silver file.

### Terraform setup

Terraform describes the static AWS infrastructure: the Glue database, the Glue table,
the Athena workgroup and an unattached least-privilege IAM policy for future analysts.
It does not register future daily partitions; those are runtime data created by Spark.

From the repository root, run:

```powershell
cd terraform
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan
```

`terraform.tfvars` is optional when the defaults are suitable. It is ignored by Git and
must never contain AWS credentials. The existing state-managed data lake bucket is used
when `data_lake_bucket_name = null`.

After reviewing the plan, create or update the AWS resources yourself:

```powershell
terraform apply
```

This command creates Glue Catalog resources, an Athena workgroup and an IAM managed
policy. It changes AWS and may incur charges, so it is intentionally not run by this
project automatically.

The Athena workgroup is named `crypto-data-platform` by default. Its enforced query
results location is:

```text
s3://<bucket>/athena-results/
```

The IAM policy produced by Terraform is deliberately not attached to any identity. Its
output ARN can later be attached to an analyst IAM role or group. This separates
data-platform resources from account-specific user and role management.

To remove the infrastructure later, first inspect the deletion plan and then run:

```powershell
terraform plan -destroy
terraform destroy
```

`terraform destroy` is destructive: it removes Terraform-managed resources and can
affect the existing state-managed S3 bucket. Do not run it while the data lake must be
preserved.

### Querying Silver with Athena

After Terraform has created the table, open Athena in the AWS Console, select the
`crypto-data-platform` workgroup and execute the SQL files in this order:

```text
sql/athena/01_repair_silver_partitions.sql
sql/athena/02_show_silver_partitions.sql
sql/athena/03_preview_silver.sql
sql/athena/04_silver_data_quality.sql
sql/athena/05_daily_price_summary.sql
```

`MSCK REPAIR TABLE` scans the Hive-style Silver paths written by Spark and registers new
`source` / `ingest_date` partitions in Glue Catalog. Run it after Silver receives new
partitions. Later, the pipeline can be improved to add only the specific successful
partition automatically.

Athena is billed by the amount of data scanned. Parquet, selecting only needed columns,
and always filtering by `source` and `ingest_date` keep queries faster and cheaper. The
preview and summary SQL files demonstrate this pattern.
