# dbt state: incremental, snapshot and audit

Implementation: 2026-11-17. Supported installed versions: dbt Core 1.12.5,
dbt-redshift 1.11.1 (locked in `dbt/requirements.lock.txt`). The installed adapter
implements `delete+insert`; its incremental materialization runs transactional
post-hooks before commit. SQL snapshots use the supported `check` strategy and
`hard_deletes='invalidate'`. See dbt's [incremental strategies](https://docs.getdbt.com/docs/build/incremental-strategy),
[snapshots](https://docs.getdbt.com/docs/build/snapshots),
[hard deletes](https://docs.getdbt.com/reference/resource-configs/hard-deletes)
and [transactional hooks](https://docs.getdbt.com/reference/resource-configs/pre-hook-post-hook).

## Objects and responsibilities

Default profile schema is `analytics`; other profile schemas replace that prefix.
No Airflow dbt automation is added. After separate user authorization, the existing
Redshift TCP 5439 ingress rule was changed to `14.236.20.114/32`, and the same value
was saved in ignored `terraform/reviewer.auto.tfvars`. No other infrastructure was changed.

| Redshift object | Kind and purpose |
| --- | --- |
| `spectrum_silver.silver_crypto_prices` | Existing external source, backed by Glue/S3 |
| `analytics_reference.crypto_symbols` | Seed table: current reviewed CSV reference |
| `analytics_staging.stg_crypto_prices` | Incremental physical table of current observations |
| `analytics_intermediate.int_crypto_prices_with_previous` | View, calculates LAG from local staging |
| `analytics_gold.gold_latest_crypto_price` | Table, completely rebuilt each run |
| `analytics_gold.gold_daily_crypto_price_summary` | Table, completely rebuilt each run |
| `analytics_snapshots.crypto_symbols_snapshot` | Physical SCD2 history table, maintained by snapshot |
| `analytics_staging.dbt_model_run_audit` | Append-only audit table created by transactional pre-hook |

Ordinary Redshift views cannot directly reference Spectrum; incremental staging
remains a local table. No downstream model currently consumes the snapshot; it is
available for historical reference analysis. The seed still enriches current prices.

## What incremental means here

The stable grain is one Raw object. Silver hashes `raw_file_path` into `record_id`;
Spark rebuilds must preserve the same path representation. Moving/renaming a Raw
object changes its key. Raw filenames have second precision: external concurrent
writers can overwrite an object; dbt cannot recover overwritten Raw history.

First run (or `--full-refresh`) selects the complete visible source. On subsequent
runs a full-source `EXCEPT` comparison returns new keys and rows whose output fields
differ from staging, with NULL-safe set semantics. Redshift `delete+insert` replaces
only those keys in one transaction. New records for any past `ingest_date` are found;
there is no date lookback limit or timestamp watermark. Corrected prices, source/date,
symbol and seed enrichment are updated. This stores current state per observation,
not previous values of that observation.

Both load timestamps are compared too. `bronze_loaded_at` already controls downstream
ordering, so retaining stale timestamps would change established latest/LAG behavior.
Spark reads all Raw/Bronze and rewrites populated partitions; replay can therefore
cause all staging rows to be replaced. With unchanged Silver/seed, the incremental
delta is empty. This reduces writes for unchanged sources but scans all Spectrum data
each run and is not a large-scale CDC solution. Neither timestamp is exchange event
time; within-day ordering remains technical.

ROW_NUMBER defensively selects one row per key (latest Silver/Bronze timestamp, then
the remaining fields for deterministic ties). It also prevents duplicate seed/source
joins from multiplying target keys. This is not a business conflict resolution policy:
source and seed uniqueness tests still fail on duplicates and must be investigated.

Missing keys are **retained** on normal incremental runs. A removal or newly invalid
source row can leave an old target row. Count/source reconciliation flags drift;
it must not be ignored. After an intentional removal, repair upstream state and run
all models with `--full-refresh`. Dynamic Spark overwrite does not remove a partition
whose entire input disappeared; full refresh cannot remove rows still visible through
Spectrum. Establish the intended upstream dataset before rebuilding. Changes to model
logic or schema may also require full refresh; `on_schema_change='fail'` avoids silently
ignoring incompatible changes. Changing comparison logic requires reviewing whether
existing rows must be rebuilt.

## Reference snapshot

`symbol` is the unique key. `check_cols` explicitly tracks `base_asset`, `quote_asset`,
`asset_name` and `is_active`. The seed has no reliable business `updated_at`, so the
`check` strategy compares values instead. Repeating snapshot on an unchanged seed
does not add versions. Changing, for example, an asset display name closes the old
version and inserts a new one.

`dbt_valid_from` is when this version was first observed by snapshot; `dbt_valid_to`
is when it stopped being current. A NULL `dbt_valid_to` marks the open version.
Intervals are interpreted as `[from, to)`. `dbt_scd_id` identifies a version, not a
symbol. Hard deletion closes the open version at the next snapshot run and preserves
history, without adding a tombstone row. Reappearance starts another open version.
Tests check version IDs, required keys/times, intervals and at most one open row.

Snapshots observe state **only at execution time**. Several intervening edits can
be missed; they cannot reconstruct earlier history or actual business effective dates.
A CSV edit is invisible until `dbt seed` updates the warehouse. Snapshot is not a
backup of all prices, and `--full-refresh` does not reset snapshot history. Do not
drop the snapshot to perform a routine refresh.

Redshift seed column widths are inferred on creation (the current `asset_name` is
VARCHAR(8)). If a CSV edit needs a wider column, run `dbt seed --full-refresh` with
the same project/profile arguments before `dbt snapshot`; this recreates the current
reference table, while the separate snapshot keeps history. Ordinary value edits
within the existing types use normal `dbt seed`.

## Audit hook and transactions

The pre-hook uses `CREATE TABLE IF NOT EXISTS` in staging's schema. It requires
CREATE permission there; a pre-existing audit table must have the documented columns.
The post-hook inserts model name, dbt `invocation_id`, and `GETDATE()` as `recorded_at`.
The timestamp records hook execution, not elapsed duration or exact commit time.
No whole-table COUNT scan, affected-row claim, or timing instrumentation is added.
No-op, initial and full-refresh runs each get one audit row.

Both hooks use dbt's default **inside-transaction** behavior; no `after_commit`,
autocommit, TRUNCATE or VACUUM is used. Model DML and audit INSERT commit together;
a model failure never reaches the post-hook, and a hook failure rolls both back.
Audit means that this model transaction succeeded, not that later dbt tests, snapshots
or other models succeeded. Audit is independent of full-refresh replacement and keeps
prior execution rows. There is no automatic retention policy. Serialize dbt executions
against a target schema, especially first creation/full refresh; this project does not
implement concurrent-run coordination. Pause ingestion and wait for active Spark jobs
before dbt/reconciliation to avoid reading an S3 overwrite in progress.

## Manual commands

From repository root in PowerShell, use the existing README connection/partition steps
first. Airflow automates ingestion through Silver; Glue partition registration,
Spectrum setup and every dbt command remain manual. Check `$LASTEXITCODE` after each
native command and stop on failure.

```powershell
. ./scripts/connect_redshift.ps1
$env:DBT_SEND_ANONYMOUS_USAGE_STATS = 'false'
# First cycle AND each subsequent cycle, after Silver is stable/partitions registered:
.\.venv-dbt\Scripts\dbt.exe seed --project-dir dbt --profiles-dir dbt
.\.venv-dbt\Scripts\dbt.exe snapshot --project-dir dbt --profiles-dir dbt
.\.venv-dbt\Scripts\dbt.exe run --project-dir dbt --profiles-dir dbt
.\.venv-dbt\Scripts\dbt.exe test --project-dir dbt --profiles-dir dbt
# Reconstruct models when needed; snapshot history and audit remain:
.\.venv-dbt\Scripts\dbt.exe run --full-refresh --project-dir dbt --profiles-dir dbt
.\.venv-dbt\Scripts\dbt.exe test --project-dir dbt --profiles-dir dbt
```

`dbt run` excludes snapshots and seeds. `dbt build` includes seeds, snapshots, models
and tests in DAG order; `ref('crypto_symbols')` ensures seed precedes staging/snapshot.
Staging and snapshot are siblings, so build may execute them concurrently. Tests can
skip downstream resources on failure; build is not one global transaction. The
explicit sequence above makes snapshot ordering clear. On an existing deployment,
ordinary `dbt run` can switch the current staging table to incremental without a
mandatory rebuild because the columns/grain are unchanged.

## Verification and acceptance boundary

Executed locally on 2026-11-17:

- Offline `dbt parse --no-partial-parse`: passed with installed Core/adapter versions.
  Manifest contains 4 models, 1 seed, 1 snapshot and 62 data tests. Both hooks are
  configured with `transaction: true`. Parsing does not execute those tests.
- `dbt/checks/check_incremental.py`: actual staging SELECT rendered with Jinja and
  executed in SQLite; first/repeat, empty delta, new and arbitrarily late observations,
  corrected price, replayed timestamps, NULL enrichment, duplicate input, retained
  deletion and full-refresh removal passed. Adapter DML, snapshot and hooks are not
  executed by this check.
- Existing `test_raw_storage.py` and `test_run_sql.py`: 5 passed.
- Both rendered staging branches and rendered audit CREATE/INSERT parse with
  SQLGlot's Redshift dialect; Python compilation of both check scripts passed.
  `git diff --check` passed. These are syntax checks, not warehouse execution.

Repeat local checks without AWS (offline variables apply only to this terminal):

```powershell
$env:DBT_REDSHIFT_HOST = 'localhost'
$env:DBT_REDSHIFT_USER = 'offline_parse'
$env:DBT_ENV_SECRET_REDSHIFT_PASSWORD = 'offline_parse_placeholder'
$env:DBT_SEND_ANONYMOUS_USAGE_STATS = 'false'
.\.venv-dbt\Scripts\dbt.exe parse --project-dir dbt --profiles-dir dbt --no-partial-parse
.\.venv-dbt\Scripts\python.exe dbt/checks/check_incremental.py
.\.venv\Scripts\python.exe -m pytest -q --tb=short tests/test_raw_storage.py tests/test_run_sql.py
.\.venv-dbt\Scripts\python.exe -m py_compile scripts/check_dbt_redshift.py
```

**Redshift isolated acceptance passed on 2026-11-17**, after the user authorized
billable queries and separately authorized the restricted ingress change above.
The original connection attempt timed out because its allowed /32 was stale.
After the rule update, the final scenario ran from 04:38 to 04:42 UTC (06:38–06:42
Europe/Kiev), using prefix `dbt_check_9b4368cfb511` in the existing `ap-southeast-1`
deployment. The script exited 0 with
`PASS: Redshift incremental/snapshot/audit lifecycle and rollback`.

| Executed check | Result |
| --- | --- |
| Initial staging load and unchanged repeat | Passed; one row, no duplicate key |
| New observation and late `2020-01-01` observation | Passed; three rows including late key |
| Existing price correction and rebuilt load timestamps | Passed; target values updated |
| Source deletion on ordinary incremental | Passed; deleted key retained as documented |
| Full refresh | Passed; deleted key removed, two unique keys remain |
| Snapshot unchanged repeat | Passed; version count unchanged |
| Asset name changed from Bitcoin to BTC test | Passed; two BTCUSDT versions, one open |
| SOLUSDT removed from isolated seed table | Passed; its open snapshot version closed |
| Seed restored, snapshot rerun, all four models built | Passed |
| Full dbt test suite on isolated objects | **62 passed, 0 warnings/errors/skips** |
| Audit for every successful staging invocation | Passed; one matching invocation/model/time row |
| Intentional division-by-zero post-hook after audit INSERT | Expected model error; both price update and audit INSERT rolled back |
| Final schema cleanup | Passed; independent SQL check found zero schemas from all three SQL attempts |

Two earlier SQL attempts exposed issues in the verifier, now fixed: prepared statements
cached an old relation OID after full refresh (disabled caching on the verifier's
connection), and an overlong test asset name exceeded the seed's inferred VARCHAR(8)
(fixture now fits the declared type). Their schemas were also cleaned. The final
intentional dbt error is part of the successful rollback test, not an unhandled failure.

Logs and compiled artifacts remain locally under ignored
`.codex-build/dbt_check_9b4368cfb511/`. Actual S3/Spectrum data and production dbt
relations were not mutated or rebuilt by that isolated scenario. This verifies
Redshift adapter execution, snapshot and hook transactions against local Redshift
fixture tables. A subsequent user-requested [full live run on the same date](E2E_CHECK_2026-11-17.md)
also passed Binance through Spectrum and Gold: 44 staging observations, 0 duplicate
keys, 62 data tests passed in each of two cycles, unchanged snapshot versions and a
matching audit row per invocation. The compiled incremental SELECT returned 0 remaining
delta rows. Live reference/business values were not synthetically changed for testing.

The billable run is authorized for this task. Once network access is available, reload
real connection variables (older state here needs an explicit deployment region):

```powershell
$env:AWS_REGION = 'ap-southeast-1' # This existing deployment; use its actual region elsewhere.
. ./scripts/connect_redshift.ps1
.\.venv-dbt\Scripts\python.exe scripts/check_dbt_redshift.py --allow-billable
```

The script copies the dbt project under ignored `.codex-build/dbt_check_<random>` and
changes only that copy's source schema. It creates uniquely named local fixture tables
and schemas in the connected database; real seeds, S3 and Spectrum are untouched.
It uses the example environment-based profile in the copy, ensuring a local profile
with a fixed production schema cannot redirect test writes.
It requires CREATE SCHEMA/table, SELECT/INSERT/UPDATE/DELETE and DROP on those test
schemas. Queries and storage may incur charges even though no infrastructure changes.

Assertions cover first/repeat runs, no duplicate keys, new/late rows, price/timestamp
corrections, retained deletion, full refresh, unchanged/changed/deleted/reappearing
snapshot entities, all dbt data tests and one audit row matching each successful
model invocation. A deliberate division-by-zero hook after the audit insert verifies
rollback of both the model update and the audit. That final dbt error is expected;
the script must still finish with PASS and exit 0. Other failures stop the scenario.

The finally block drops only the generated schemas, including on assertion failures.
If the process is killed or cleanup fails, inspect the printed `dbt_check_<random>`
prefix and remove only those schemas; generated artifacts are retained for inspection.
Never run a mutation scenario against real reference or Silver data. Review the
script before running it and retain its output as the new runtime evidence.
