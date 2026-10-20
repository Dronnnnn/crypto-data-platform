# Crypto Data Platform

Binance → Airflow → S3 Raw → Spark Bronze/Silver → Glue → Spectrum → dbt → Redshift Gold.
The project demonstrates sources/ref, a reference seed, layered models, windows, two
marts, generic/reconciliation tests and docs. The assessment covers the six supplied
criteria only: no Material assignment link was provided.

## Prerequisites

Supported walkthrough: **Windows 11 x64, PowerShell 7, Python 3.11.9**. Install Git,
Docker Desktop with Linux engine running (8 GB RAM, 4 CPUs, 15 GB free disk), Compose
v2.24+ (local CLI: 5.2.0), Terraform 1.15.7 and AWS CLI v2 (local: 2.35.16).
Native Windows Spark is outside the supported path. Airflow is 3.3.0/Python 3.11;
Spark is 3.5.6; dbt Core is 1.12.5 with dbt-redshift 1.11.1. dbt transitive dependencies
are pinned in `dbt/requirements.lock.txt`; Airflow/local Python use checked-in upstream
constraints and exact direct requirements. Docker tags and OS packages are not byte-identical locks.

Cloud steps below create **billable AWS resources**. Obtain authorization before
running them. Local checks at the end require no AWS. Use `ap-southeast-1` and keep
the default database/table names because example SQL references those names.

Use a dedicated sandbox deployment role with AdministratorAccess, or an administrator
provided equivalent covering S3, Glue, Athena, IAM role/policy creation and PassRole,
EC2 network Describe, Redshift Serverless, Secrets Manager, CloudWatch logs and service-linked
roles. Broad deployment access is a sandbox convenience, not a runtime policy.
Ingestion needs bucket List/GetLocation and Get/PutObject on raw/bronze/silver/quarantine.
Querying needs Athena Start/Get/StopQueryExecution/GetQueryResults, Glue metadata read,
Glue CreatePartition/BatchCreatePartition for MSCK, and S3 Silver/results access.
Password loading needs redshift-serverless:GetNamespace and secretsmanager:GetSecretValue
on the managed secret (kms:Decrypt for a customer KMS key). The Terraform analyst policy
is unattached and does not grant partition creation. Spectrum has its own Silver/Glue role.

The account must have a default VPC with at least three supported AZ default subnets,
sufficient free IPs and routes to an attached internet gateway. VPC Block Public Access
and organizational policy must permit this review deployment. If absent, stop and ask
the account administrator to provision a suitable sandbox default VPC; this project
does not silently modify shared VPC routing.

## Clean-clone walkthrough

Clone your repository URL (`git clone <repository-url>`), then `Set-Location crypto-data-platform`.
Run every block below in the **same PowerShell terminal**, from the repository root.
Check native command exit codes (`$LASTEXITCODE`); stop on any failure.

### 1. Host authentication and local installation

```powershell
py -3.11 --version
docker info
docker compose version
terraform version
aws --version
aws configure sso --profile crypto-review
aws sso login --profile crypto-review
$env:AWS_PROFILE = 'crypto-review'
$env:AWS_REGION = 'ap-southeast-1'
$env:AWS_DEFAULT_REGION = $env:AWS_REGION
aws sts get-caller-identity
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local.txt
.\.venv\Scripts\python.exe scripts/bootstrap.py
```

For SSO, enter the start URL, SSO region, account and permission set supplied by your
administrator; use `ap-southeast-1` as client region and JSON output. An existing host
profile can replace SSO by setting AWS_PROFILE. Expected: STS shows the intended account/role.
The bootstrap copies `.env.example` to `.env` if absent and generates missing Fernet,
API session, JWT keys and a local UI password without printing them. Existing nonempty
values are preserved. Never commit `.env` or print expanded Compose configuration.

### 2. Deploy with one concrete dbt connection path

This walkthrough opts into a public TLS endpoint restricted to **one client IPv4 /32**.
Terraform defaults stay private. Validation rejects broader client networks, including
/0. The default-subnet routing prerequisite is described above; see
[AWS networking requirements](https://docs.aws.amazon.com/redshift/latest/mgmt/rs-security-group-public-private.html).

```powershell
Copy-Item terraform/terraform.tfvars.example terraform/terraform.tfvars
$clientIp = (Invoke-RestMethod 'https://checkip.amazonaws.com').Trim()
[System.Net.IPAddress]::Parse($clientIp) | Out-Null
@('redshift_publicly_accessible = true', ('redshift_allowed_cidr = "{0}/32"' -f $clientIp)) |
  Set-Content terraform/reviewer.auto.tfvars
New-Item -ItemType Directory -Force .codex-build | Out-Null
terraform -chdir=terraform init -lockfile=readonly
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
terraform -chdir=terraform plan -out=../.codex-build/review.tfplan
# Inspect the plan. The following command creates BILLABLE resources.
terraform -chdir=terraform apply ../.codex-build/review.tfplan
$bucket = terraform -chdir=terraform output -raw catalog_bucket_name
if ($LASTEXITCODE -ne 0) { throw 'Missing bucket output' }
.\.venv\Scripts\python.exe scripts/bootstrap.py --bucket $bucket
.\.venv\Scripts\python.exe scripts/export_aws_credentials.py
```

Expected: S3, Glue database/table, Athena workgroup, namespace/workgroup, security group
and Spectrum IAM role. Keep `data_lake_bucket_name = null` for this walkthrough.
`catalog_bucket_name` identifies the actual Glue bucket even when overridden. State/plans
are ignored and may contain sensitive metadata; retain them securely for future teardown.
The exporter freezes the host session into ignored `.aws-runtime/credentials`, mounted
read-only at each container user's `.aws` for boto3 and Java S3A. Refresh SSO and re-run
the exporter before session expiration, then recreate containers. Do not share this directory.

### 3. Ingest and build Silver

```powershell
docker compose config --quiet
docker compose build
docker compose up airflow-init
docker compose up -d airflow-apiserver airflow-scheduler airflow-dag-processor airflow-triggerer spark-master spark-worker
docker compose ps
docker compose exec airflow-scheduler airflow dags list-import-errors
docker compose exec airflow-scheduler airflow dags list
$runDate = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd')
$runId = 'review_' + (Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmss')
docker compose exec airflow-scheduler airflow dags unpause binance_ingestion
docker compose exec airflow-scheduler airflow dags trigger --run-id $runId binance_ingestion
docker compose exec airflow-scheduler airflow dags list-runs -d binance_ingestion
```

Expected: init exits 0; Airflow becomes healthy, Spark runs, no import errors. Repeat
list-runs until the chosen run succeeds: ingest_raw, raw_to_bronze, bronze_to_silver
must all succeed. Binance must be accessible from your network/country; HTTP 451/403 is
a blocker. Default symbol: BTCUSDT. To change it, add the symbol to the seed and set
AIRFLOW_VAR_SYMBOL in `.env`, then recreate containers. SMTP is optional; failure mail
is disabled unless EMAILS is configured.

Open [Airflow](http://localhost:8080) as `airflow`; read the generated
_AIRFLOW_WWW_USER_PASSWORD in your local `.env` editor, never shared terminal output.
[Spark UI](http://localhost:8081) should show completed applications. If the run crosses
UTC midnight, explicitly set `$runDate` to the ingest_date in that run's Raw object key.

```powershell
aws s3 ls "s3://$bucket/raw/source=binance/symbol=BTCUSDT/ingest_date=$runDate/"
aws s3 ls "s3://$bucket/silver/crypto_prices/source=binance/ingest_date=$runDate/" --recursive
docker compose exec airflow-scheduler airflow dags pause binance_ingestion
```

Expected: nonempty Raw JSON and at least one nonempty Silver part-*.parquet for that
date. Wait for **all active runs** to finish before SQL checks. Runs are serialized.
Spark rebuilds present input partitions; dynamic overwrite does not delete stale
partitions if all their input disappears. Do not manually delete input in this scenario.

### 4. Install dbt and load the connection securely

```powershell
py -3.11 -m venv .venv-dbt
.\.venv-dbt\Scripts\python.exe -m pip install -r dbt/requirements.lock.txt
.\.venv-dbt\Scripts\python.exe -m pip check
Copy-Item dbt/profiles.yml.example dbt/profiles.yml
. ./scripts/connect_redshift.ps1
Test-NetConnection $env:DBT_REDSHIFT_HOST -Port ([int]$env:DBT_REDSHIFT_PORT)
```

Expected: no broken requirements and TcpTestSucceeded=True. Dot-sourcing loads endpoint,
port, DB and namespace from Terraform outputs, reads the managed secret ARN using
get-namespace and captures get-secret-value directly into memory. It exports
DBT_ENV_SECRET_REDSHIFT_PASSWORD, which dbt masks, and never prints/writes the password.
Do not enable shell tracing. The profile requires TLS; the SQL helper verifies the
certificate. If your public IP changes, regenerate reviewer.auto.tfvars and review/apply
a new plan. Check local firewall/VPC routing; never broaden ingress.

### 5. Register partitions and create Spectrum schema

The following queries incur AWS charges. The helper replaces `${RUN_DATE}` only after
validating its ISO date; do not paste unresolved placeholders into a SQL editor.

```powershell
foreach ($file in (Get-ChildItem sql/athena/*.sql | Sort-Object Name)) {
  .\.venv-dbt\Scripts\python.exe scripts/run_sql.py --engine athena --file $file.FullName --date $runDate
  if ($LASTEXITCODE -ne 0) { throw "Athena check failed: $file" }
}
.\.venv-dbt\Scripts\python.exe scripts/run_sql.py --engine redshift --file sql/redshift/01_create_external_schema.sql --date $runDate
.\.venv-dbt\Scripts\python.exe scripts/run_sql.py --engine redshift --file sql/redshift/02_preview_spectrum_silver.sql --date $runDate
```

Expected: MSCK succeeds; SHOW PARTITIONS includes the chosen source/date; previews and
daily aggregate return rows; all invalid/duplicate counts are zero and run_date_rows>0.
Spectrum must return that date's rows too. Empty data is a failed acceptance check even
without SQL exceptions. The external schema uses the namespace's default Spectrum role.

### 6. Build, test and inspect Gold

```powershell
$env:DBT_SEND_ANONYMOUS_USAGE_STATS = 'false'
.\.venv-dbt\Scripts\dbt.exe debug --project-dir dbt --profiles-dir dbt
.\.venv-dbt\Scripts\dbt.exe seed --project-dir dbt --profiles-dir dbt
.\.venv-dbt\Scripts\dbt.exe run --project-dir dbt --profiles-dir dbt
.\.venv-dbt\Scripts\dbt.exe test --project-dir dbt --profiles-dir dbt
.\.venv-dbt\Scripts\dbt.exe docs generate --project-dir dbt --profiles-dir dbt
.\.venv-dbt\Scripts\python.exe scripts/run_sql.py --engine redshift --file sql/redshift/03_preview_gold_marts.sql --date $runDate
.\.venv-dbt\Scripts\dbt.exe docs serve --project-dir dbt --profiles-dir dbt --port 8082
```

Expected: successful debug connection, seed loaded, 4 models built, all 54 tests pass,
catalog/manifest generated. Both Gold tables and selected-date counts must be nonempty;
observations must equal Silver's count for the date. Schemas are analytics_staging,
analytics_intermediate, analytics_gold and analytics_reference: dbt appends custom schemas
to the profile schema. Inspect lineage in [docs](http://localhost:8082); Ctrl+C stops it.
Close the terminal or remove Env:DBT_ENV_SECRET_REDSHIFT_PASSWORD afterwards.

Tests reject empty source/staging/intermediate/seed/marts, null/duplicate keys,
nonpositive prices, missing timestamps, unknown seed symbols. Full outer joins reconcile
daily groups/count/min/max/average (tolerance 1e-8) and latest observations. Source/staging
counts detect silently filtered rows. Pause ingestion to keep inputs stable during checks.

## Architecture decisions and oral review notes

| Layer/model | Grain/key | Decision |
| --- | --- | --- |
| Raw | One landed payload/S3 key | Original JSON for replay; filenames have second precision, so avoid concurrent external writers |
| Bronze/Silver | One Raw object; SHA-256 record_id in Silver | DECIMAL(20,8), validation/quarantine, Parquet by source/date |
| Spectrum source | Same observation | Glue supplies schema/partitions; data remains in S3 |
| crypto_symbols seed | One symbol, unique symbol | Small reviewed enrichment/allowed-symbol reference |
| stg_crypto_prices | One observation, unique record_id | Table standardizes Spectrum; ordinary schema-bound views cannot directly query Spectrum |
| int_crypto_prices_with_previous | One observation, unique record_id | Reusable LAG view per source/symbol |
| gold_latest_crypto_price | One source/symbol, MD5 composite key | ROW_NUMBER selects latest technical observation; consumer table |
| gold_daily_crypto_price_summary | One source/date/symbol, MD5 composite key | Consumer table with count/min/max/average |

bronze_loaded_at is **processing time**, not exchange event time. Batch timestamps may
tie; record_id creates deterministic order, not proof of exchange chronology. Rebuilding
Bronze changes technical timestamps. Price changes compare technical observations.
Full rebuilds suit this dataset's size; incremental/snapshots are not added for checklist
coverage. Snapshots suit changing entity state rather than individual price observations.
Glue is metadata, Athena explores Parquet, Spectrum connects lake and warehouse, dbt owns
warehouse transformations/contracts. Event time, retention, production deployment roles
and incremental ingestion need separate design.

## Local checks and acceptance boundary

```powershell
# Offline-only placeholders; no SQL connection is made by parse.
$env:DBT_REDSHIFT_HOST = 'localhost'
$env:DBT_REDSHIFT_USER = 'offline_parse'
$env:DBT_ENV_SECRET_REDSHIFT_PASSWORD = 'offline_parse_placeholder'
$env:DBT_SEND_ANONYMOUS_USAGE_STATS = 'false'
.\.venv-dbt\Scripts\dbt.exe parse --project-dir dbt --profiles-dir dbt --no-partial-parse
$env:S3_BUCKET = 'offline-test-bucket'
.\.venv\Scripts\python.exe -m pytest -q --tb=short tests/test_raw_storage.py tests/test_run_sql.py
docker compose --profile test run --rm --build spark-tests
terraform -chdir=terraform init -backend=false -lockfile=readonly
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
# Install Gitleaks 8.30.0 separately to repeat secret scanning:
gitleaks git . --log-opts='--all' --redact=100
gitleaks dir . --config .gitleaks.toml --redact=100
```

parse checks configuration/Jinja/dependencies; it does **not** execute Redshift SQL.
Real acceptance requires the cloud steps and nonempty results. This offline block
replaces connection variables; re-run connect_redshift.ps1 before real SQL. Directory
scanning intentionally includes ignored `.env`: local secrets may be found without
being Git leaks. Dependency caches/generated output are excluded. Do not print findings'
values. See [security cleanup](docs/SECURITY.md) and [audit evidence](docs/AUDIT.md).

Stop services with `docker compose down` (no -v, preserving PostgreSQL data). AWS remains
billable separately. To retire the sandbox, preserve necessary data/state, inspect
`terraform -chdir=terraform plan -destroy`, then explicitly authorize and execute
`terraform -chdir=terraform destroy`. Nonempty buckets may block destruction; do not
delete contents without a data-retention decision.

The original audit did not deploy AWS. Separately authorized follow-ups cleaned local
history and prepared the source commit/publication (see docs/SECURITY.md and docs/AUDIT.md).
Keep local `.env`, credentials, tfvars/state/plans, caches/logs/build output and unrelated
output presentations out of Git. Separately review the user's preexisting source/test/data
deletions; do not silently restore or stage them with git add -A.
