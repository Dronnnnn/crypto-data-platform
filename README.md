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
- Amazon Redshift Serverless
- dbt Core with dbt-redshift

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
  -> Redshift Spectrum
  -> dbt
  -> Redshift Gold marts
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

## Redshift Serverless, Spectrum, and dbt

This stage adds a warehouse serving layer without moving Silver Parquet files out of S3:

```text
S3 Silver Parquet
  -> Glue Data Catalog table
  -> Redshift Spectrum external schema
  -> dbt staging and intermediate models
  -> Redshift Gold tables
```

### Components and responsibilities

- A **Redshift Serverless namespace** is the logical warehouse container. It owns the
  initial database (`crypto_warehouse`), users, metadata, and the IAM role attached to
  the warehouse.
- A **Redshift Serverless workgroup** provides the compute capacity and SQL endpoint.
  It is the serverless replacement for manually operating a Redshift cluster.
- **Redshift Spectrum** is Redshift's ability to query external S3 data. The schema
  `spectrum_silver` references the Glue database `crypto_data_lake`; it does not copy
  `silver_crypto_prices` into Redshift.
- A **dbt source** is an existing input relation that dbt reads but does not build. In
  this project it is `spectrum_silver.silver_crypto_prices`.
- A **dbt model** is version-controlled SQL that dbt builds. `staging` standardizes the
  source into a regular Redshift table, `intermediate` keeps reusable calculations, and
  `marts` contains Gold tables intended for analytics consumers. The staging model must
  be a table rather than a view because Redshift does not allow ordinary views to select
  directly from Spectrum external tables.

The `gold_latest_crypto_price` mart uses `bronze_loaded_at` as the best currently
available technical ordering field. It is not an exchange event time: records in one
Spark batch can share it, so `record_id` is used as a deterministic tie-breaker. A future
source that provides a genuine event timestamp should add `event_time` to the Silver
contract and use it as the primary ordering field.

No dbt snapshot is included yet. A snapshot models slowly changing state; a stream of
individual crypto price observations is not such an entity. A future reference dataset
(for example, symbol metadata with changing status) is a better first snapshot target.

### Redshift networking and IAM

Terraform discovers the account's default VPC and default subnets when it creates the
workgroup. The default is deliberately private:

```hcl
redshift_publicly_accessible = false
```

No inbound security-group rule is created in this mode. To connect dbt from a laptop,
use a secure private path such as VPN, an SSM-managed EC2 instance, or a CI runner in the
same VPC. Public access is a deliberate development-only opt-in: set
`redshift_publicly_accessible = true` and provide exactly one trusted public client CIDR
in `redshift_allowed_cidr`; never use `0.0.0.0/0`.

Terraform creates a separate **Redshift Spectrum IAM role**. It can read only
`silver/*` from the project bucket and the required Glue metadata. This is different from
the Athena analyst policy: the analyst policy represents a person or BI client, while the
Spectrum role is assumed by the Redshift service while it reads S3 on behalf of SQL.

### Deploying Redshift infrastructure

From the repository root:

```powershell
cd terraform
terraform fmt -check
terraform validate
terraform plan
```

`terraform plan` reads the default VPC and subnets in the configured AWS region. It must
show the namespace, workgroup, security group, Spectrum IAM role and its policy before
you apply it. Creating a Serverless workgroup can incur Redshift charges:

```powershell
terraform apply
```

After apply, obtain the endpoint and database name without exposing a password:

```powershell
terraform output redshift_endpoint_host
terraform output redshift_endpoint_port
terraform output redshift_database_name
terraform output redshift_spectrum_role_arn
```

AWS manages the admin password in Secrets Manager because the namespace uses
`manage_admin_password = true`. Retrieve it only when configuring a private local dbt
environment; do not put it in Git, a Terraform output, or `profiles.yml`.

### Spectrum setup and verification

Connect to `crypto_warehouse` using Redshift Query Editor v2 or a network path allowed by
the workgroup security group. Run these version-controlled SQL files in order:

```text
sql/redshift/01_create_external_schema.sql
sql/redshift/02_preview_spectrum_silver.sql
```

The first statement uses `IAM_ROLE default`. Terraform already attaches the Spectrum role
as the namespace default role, so an ARN does not need to be copied into SQL. The preview
filters by `source` and `ingest_date`, preserving partition pruning while Spectrum reads
the external Parquet table.

### dbt project

The dbt project is in [`dbt/`](dbt). Install the adapter in a dedicated local virtual
environment:

```powershell
python -m venv .venv-dbt
.\.venv-dbt\Scripts\Activate.ps1
pip install -r dbt\requirements.txt
Copy-Item dbt\profiles.yml.example dbt\profiles.yml
```

Set connection values in your shell environment, not in Git:

```text
DBT_REDSHIFT_HOST
DBT_REDSHIFT_PORT
DBT_REDSHIFT_DBNAME
DBT_REDSHIFT_USER
DBT_REDSHIFT_PASSWORD
DBT_REDSHIFT_SCHEMA
```

dbt reads operating-system environment variables; it does not load the project's `.env`
file automatically. In PowerShell, export the values for the current terminal session
after retrieving the endpoint and the Secrets Manager password through an approved secure
path:

```powershell
$env:DBT_REDSHIFT_HOST = "<Redshift endpoint from Terraform output>"
$env:DBT_REDSHIFT_PORT = "5439"
$env:DBT_REDSHIFT_DBNAME = "crypto_warehouse"
$env:DBT_REDSHIFT_USER = "adminuser"
$env:DBT_REDSHIFT_PASSWORD = "<password from AWS Secrets Manager>"
$env:DBT_REDSHIFT_SCHEMA = "analytics"
```

Run dbt from the `dbt` directory. `--profiles-dir .` makes dbt use the local untracked
profile template you copied above.

```powershell
cd dbt
dbt debug --profiles-dir .
dbt seed --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .
```

`dbt seed`, `dbt run`, and `dbt test` execute SQL in Redshift. Source tests can make
Spectrum scan S3, while models build Redshift views and Gold tables; all three can incur
cost. `dbt docs generate` reads project metadata and warehouse metadata, and `dbt docs
serve` starts only a local documentation server.

After dbt completes, verify Gold tables with:

```text
sql/redshift/03_preview_gold_marts.sql
```

To remove infrastructure later, inspect the deletion plan before using `terraform
destroy`. It is destructive and includes the existing Terraform-managed data lake bucket;
never run it while the platform data must be retained.
