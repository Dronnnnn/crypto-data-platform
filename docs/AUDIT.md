# dbt pet-project audit — 2026-10-20

Scope: the six criteria supplied in the pasted request. No Material assignment link
was available; no additional rubric is inferred. AGENTS.md was not found in the repo
or its parent directories. Existing user changes were inspected before editing.

## Authorized follow-up: local history cleaned

After the original audit the user explicitly authorized history rewriting, but not
force-push. All five refs, including three Codex tree snapshots, now exclude the entire
airflow/config/airflow.cfg path. main is 84e1fe758320d7b2eb3e98b69ddd354323c2ff57;
the available commit count remains 10. No new commit of the prepared working changes
was created. Safe current config is preserved as untracked and must be included in the
future reviewed source commit. Hash verification preserved all 87 existing working files
and all unrelated index entries, including user changes and staged removals.

Gitleaks --all --reflog: zero findings after cleanup; git fsck: PASS. The Windows
DPAPI-encrypted recovery archive and bundle restoration were verified. Old root reflogs
and unreachable objects were cleaned; agent-created temporary plaintext Git copies
were removed. No push, remote update, AWS operation or key rotation was performed.
See SECURITY.md for the recovery path and remaining remote/rotation actions. The original
audit evidence below records what was true before this authorized follow-up.

## Authorized publication follow-up

The user subsequently requested committing and pushing the prepared changes. The source
commit includes audit fixes, safe Airflow config, documentation, dependency pins, tests
and the staged egg-info/tfvars removals. Six unrelated preexisting file deletions remain
unstaged. Before publication, origin/main was verified at the expected original tip
b3304af9af1968f9a494fff602a91284816cf11c. The publication workflow uses an explicit
force-with-lease for that tip, updating main only, and verifies the remote tip afterwards.
Statements below about changes awaiting authorization describe the original audit.

## Changes prepared

- Removed egg-info and terraform/terraform.tfvars from the Git index. The existing
  modified local tfvars was preserved; terraform.tfvars.example remains versioned.
- Expanded ignores for virtualenvs, local credentials/env/tfvars/state, dbt packages,
  build output, caches/logs and unrelated output presentations. Added .dockerignore.
- Replaced generated Airflow config with minimal safe configuration. Required API
  session/JWT/Fernet/UI secrets come from environment. Bootstrap preserves existing
  nonempty values. UI ports bind to loopback. Optional mail is off without recipients.
- Pinned direct requirements, checked in upstream Airflow constraints and the resolved
  dbt environment lock. dbt uses the masked DBT_ENV_SECRET_REDSHIFT_PASSWORD variable
  and verify-full TLS. Added host-session export for boto3/Java container credentials.
- Documented one public TLS Redshift connection path restricted to a single IPv4 /32.
  Terraform rejects broad client CIDRs; private remains the default. Added outputs
  for namespace and effective catalog bucket and a safe managed-password loader.
- Rewrote README with a clean-clone PowerShell sequence, prerequisites/permissions,
  expected outputs, UTC date selection, partition registration, Spectrum setup, dbt
  execution and nonempty Gold checks. Added repeatable SQL/bootstrap/auth helpers.
- Preserved source/ref, staging/intermediate/marts, seed, LAG and ROW_NUMBER. Added
  not-empty tests for all key relations, seed uniqueness/metadata checks, timestamp
  requirements and daily/latest/count reconciliation. Total parsed tests: 54.
- Raw JSON now uses recursiveFileLookup so Hive's symbol partition cannot replace
  the payload's symbol and hide a mismatch. Added a regression test. DAG runs are
  serialized to avoid overlapping full-partition overwrites.
- Added architecture/grain/materialization/ordering limitations and oral review notes
  in README, and a concrete redacted history-cleanup procedure in SECURITY.md.

## Executed checks and actual limits

An isolated local clone was created under ignored .codex-build/review, then overlaid
with the proposed current source, including user deletions. No .env, local profile,
Terraform state, cache or existing venv was copied. This is a proposed-change rehearsal,
not proof that the uncommitted changes already exist in a remote clone.

| Check | Result |
| --- | --- |
| Clean Python 3.11 venv install with requirements-local.txt | PASS |
| Clean dbt venv install from requirements.lock.txt | PASS |
| pip check in both clean environments | PASS |
| Bootstrap from template; second invocation preserves configuration byte-for-byte | PASS |
| docker compose config --quiet using generated clone settings | PASS; no secrets printed |
| PowerShell connection script syntax | PASS; AWS execution not attempted |
| Terraform clean-clone init -backend=false -lockfile=readonly | PASS; AWS provider 6.53.0 downloaded and signed |
| Terraform fmt -check / validate | PASS (provider validation required unsandboxed local process access) |
| dbt parse --no-partial-parse with copied example profile and offline placeholders | PASS: 4 models, 1 seed, 1 source, 54 tests; no SQL execution |
| Raw upload test with mocked S3 + SQL helper regression/date substitution in clean clone | PASS: 3 tests |
| Native Spark transformation tests in clean venv | 8 PASS; new filesystem regression FAILS before reading due missing Hadoop Windows NativeIO library |
| Python compile / scoped Ruff / git diff --check | PASS |
| Ignore/index audit | PASS: no tracked egg-info, state, dependency caches, dbt outputs or local tfvars remain in the index |
| Gitleaks 8.30.0, git --all | 10 commits scanned, 2 historical signing-secret findings in airflow.cfg |
| Gitleaks current directory, dependencies/generated output excluded | 1 expected local ignored .env Fernet finding; no current source finding |

Docker CLI is installed but Docker Desktop Linux Engine is unavailable. Therefore no
image build, container Spark test, DAG import/runtime or Docker end-to-end execution
is claimed. Native Spark initially hit sandbox Java-gateway restrictions; with local
process access 8 tests passed, and the filesystem regression exposed the host's missing
native Hadoop library. The documented Docker test path is still required for acceptance.
AWS plan/apply, queries, DAG execution, dbt debug/seed/run/test/docs generate against
Redshift were deliberately NOT executed: billable/cloud work was not authorized.
The SQL helper and managed-password loader have local syntax/unit coverage only.

## Six-criterion status

| Criterion | Status | Remaining acceptance action |
| --- | --- | --- |
| 1. Committed sources; clean Git | PARTIAL | Review and commit prepared changes; no commit was authorized |
| 2. Exact build/run/deploy README | DOCUMENTED, partially validated | Execute remaining Docker/cloud blocks and record evidence |
| 3. Reproduce from README only | NOT YET PROVEN end-to-end | Start Docker Engine; authorize sandbox AWS work; finish README steps 2–6 |
| 4. Nontrivial dbt functionality | PRESENT, parsed locally | Execute models and 54 tests on nonempty Redshift inputs |
| 5. No secrets in files/history | LOCAL history clean; remote not yet cleaned | Rotate used signing secrets; authorize force-push after reviewed fixes are committed; rescan remote clone |
| 6. Author can explain architecture | NOTES PREPARED | Use README's grain/materialization/ordering notes in oral review |

## Blockers and exact next actions

1. Start Docker Desktop's Linux engine, confirm docker info, then run
   `docker compose --profile test run --rm --build spark-tests` to verify all 9 Spark
   tests, including actual JSON partition reading. A native Windows DLL workaround
   is not necessary for the supported Docker path.
2. Obtain authorization for billable AWS work and an appropriately permissioned sandbox
   profile/default VPC. Follow README steps 2–6. Keep ingestion paused during warehouse
   checks. Require nonempty selected-date Silver and both Gold marts and all tests PASS.
3. Rotate any used historical Airflow API/JWT signing keys. The initial failed native
   Spark traceback included AZDO_FEED_PAT from the process environment; revoke/replace
   that token with its issuer as well. No token values are recorded in these documents.
4. Local history rewriting was separately authorized and completed. Obtain separate
   permission before force-push. SECURITY.md records the cleanup, encrypted recovery
   archive, affected file/keys and remaining coordinated remote/rescan procedure.
5. Review and selectively commit the prepared changes listed below. No commits/push,
   rewrite or cloud modifications were performed.

## What to commit for criterion 1

Review the modifications to .env.example, .gitignore, Dockerfile, README.md,
airflow/config/airflow.cfg, airflow/dags/binance_ingestion.py, docker-compose.yml,
pyproject.toml, requirements-airflow.txt, spark/Dockerfile.test,
spark/jobs/bronze_binance.py, tests/test_bronze_binance.py, dbt model YAMLs,
dbt/profiles.yml.example, dbt/requirements.txt, SQL date/verification files,
terraform/outputs.tf, terraform/variables.tf, terraform/versions.tf and
terraform/terraform.tfvars.example. Add new .dockerignore, .gitleaks.toml,
constraints-airflow.txt, requirements-local.txt, scripts/*.py,
scripts/connect_redshift.ps1, tests/test_run_sql.py, docs/AUDIT.md, docs/SECURITY.md,
dbt/requirements.lock.txt, dbt/seeds/crypto_symbols.yml,
dbt/models/intermediate/int_crypto_prices_with_previous.yml and the four new dbt tests
(not_empty generic plus daily/latest/staging-count singular tests).
Include the already staged index removals for egg-info and terraform/terraform.tfvars.

Preexisting user deletions were preserved and must be reviewed separately:
data/test.json, src/crypto_data_platform/common/aws.py,
src/crypto_data_platform/ingestion/uploader.py, src/crypto_data_platform/models/__init__.py,
src/crypto_data_platform/models/price.py and tests/conftest.py. Do not use a blanket
git add -A to accidentally decide their fate. Local .env/tfvars/credentials/state,
output presentations and .codex-build rehearsal artifacts must not be committed.
