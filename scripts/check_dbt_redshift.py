"""Billable opt-in integration check; all writes confined to unique test schemas."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import redshift_connector
import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-billable', action='store_true', required=True)
    parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    schema = 'dbt_check_' + uuid.uuid4().hex[:12]
    project = root / '.codex-build' / schema
    shutil.copytree(root / 'dbt', project,
                    ignore=shutil.ignore_patterns('target', 'logs', 'profiles.yml', '.user.yml'))
    # Use a known env-based profile, never a local profile with a fixed production
    # schema. This file contains placeholders only, not expanded credentials.
    shutil.copyfile(root / 'dbt/profiles.yml.example', project / 'profiles.yml')
    # Rewrite only the disposable project copy. Never address the real Spectrum source.
    source_path = project / 'models/sources/spectrum_silver.yml'
    sources = yaml.safe_load(source_path.read_text(encoding='utf-8'))
    sources['sources'][0]['schema'] = schema + '_fixtures'
    source_path.write_text(yaml.safe_dump(sources), encoding='utf-8')
    env = {**os.environ, 'DBT_REDSHIFT_SCHEMA': schema,
           'DBT_SEND_ANONYMOUS_USAGE_STATS': 'false'}
    connection = redshift_connector.connect(
        host=env['DBT_REDSHIFT_HOST'], port=int(env.get('DBT_REDSHIFT_PORT', '5439')),
        database=env.get('DBT_REDSHIFT_DBNAME', 'crypto_warehouse'),
        user=env['DBT_REDSHIFT_USER'], password=env['DBT_ENV_SECRET_REDSHIFT_PASSWORD'],
        ssl=True, sslmode='verify-full', timeout=30,
        # dbt full-refresh swaps relation OIDs on a different connection. Do not
        # reuse this verifier's prepared statements against the old relation.
        max_prepared_statements=0,
    )
    connection.autocommit = True

    def sql(statement):
        with connection.cursor() as cursor:
            cursor.execute(statement)
            return cursor.fetchall() if cursor.description else []

    def expect(statement, value):
        actual = sql(statement)[0][0]
        if actual != value:
            raise AssertionError(f'{statement}: expected {value}, got {actual}')

    def dbt(*args, fails=False):
        result = subprocess.run(
            [str(Path(sys.executable).with_name('dbt.exe' if os.name == 'nt' else 'dbt')),
             *args, '--project-dir', str(project), '--profiles-dir', str(project)],
            env=env, cwd=root, check=False,
        )
        if (result.returncode != 0) != fails:
            raise RuntimeError(f'Unexpected dbt exit code {result.returncode}: {args}')
        if fails:
            artifact = json.loads((project / 'target/run_results.json').read_text())
            if not any(r['status'] == 'error' and any(
                phrase in str(r.get('message', '')).lower()
                for phrase in ('divide by zero', 'division by zero')
            ) for r in artifact['results']):
                raise AssertionError('Expected the deliberate division-by-zero hook failure')
        if not fails and args[0] == 'run':
            artifact = json.loads((project / 'target/run_results.json').read_text())
            invocation = artifact['metadata']['invocation_id']
            expect(f"SELECT COUNT(*) FROM {audit} WHERE invocation_id='{invocation}' "
                   "AND model_name='stg_crypto_prices' AND recorded_at IS NOT NULL", 1)

    fixtures = schema + '_fixtures.silver_crypto_prices'
    staging = schema + '_staging.stg_crypto_prices'
    audit = schema + '_staging.dbt_model_run_audit'
    snapshot = schema + '_snapshots.crypto_symbols_snapshot'
    reference = schema + '_reference.crypto_symbols'
    print(f'Isolated Redshift check: {schema}', flush=True)
    try:
        sql(f'CREATE SCHEMA {schema}_fixtures')
        sql(f'''CREATE TABLE {fixtures} (record_id VARCHAR(64), source VARCHAR(32),
            ingest_date DATE, symbol VARCHAR(32), price NUMERIC(20,8),
            bronze_loaded_at TIMESTAMP, silver_loaded_at TIMESTAMP)''')
        sql(f"INSERT INTO {fixtures} VALUES "
            "('a','binance','2026-11-17','BTCUSDT',100,'2026-11-17','2026-11-17')")
        dbt('seed')
        dbt('run', '--select', 'stg_crypto_prices')
        expect(f'SELECT COUNT(*) FROM {staging}', 1)
        dbt('run', '--select', 'stg_crypto_prices')
        expect(f'SELECT COUNT(*) FROM {staging}', 1)
        sql(f"INSERT INTO {fixtures} VALUES "
            "('b','binance','2026-11-18','BTCUSDT',110,'2026-11-18','2026-11-18'),"
            "('late','binance','2020-01-01','BTCUSDT',90,'2020-01-01','2020-01-01')")
        sql(f"UPDATE {fixtures} SET price=105 WHERE record_id='a'")
        dbt('run', '--select', 'stg_crypto_prices')
        expect(f'SELECT COUNT(*) FROM {staging}', 3)
        expect(f"SELECT price FROM {staging} WHERE record_id='a'", 105)
        expect(f"SELECT COUNT(*) FROM {staging} WHERE ingest_date='2020-01-01'", 1)
        sql(f"UPDATE {fixtures} SET bronze_loaded_at='2026-11-19', silver_loaded_at='2026-11-19'")
        dbt('run', '--select', 'stg_crypto_prices')
        expect(f"SELECT COUNT(*) FROM {staging} WHERE silver_loaded_at='2026-11-19'", 3)
        sql(f"DELETE FROM {fixtures} WHERE record_id='late'")
        dbt('run', '--select', 'stg_crypto_prices')
        expect(f'SELECT COUNT(*) FROM {staging}', 3)  # documented retained deletion
        dbt('run', '--select', 'stg_crypto_prices', '--full-refresh')
        expect(f'SELECT COUNT(*) FROM {staging}', 2)
        expect(f'SELECT COUNT(*)-COUNT(DISTINCT record_id) FROM {staging}', 0)
        dbt('snapshot')
        original = sql(f'SELECT COUNT(*) FROM {snapshot}')[0][0]
        dbt('snapshot')
        expect(f'SELECT COUNT(*) FROM {snapshot}', original)
        # Seed inference currently creates VARCHAR(8); keep the fixture within
        # that declared width so this tests SCD behavior, not a schema migration.
        sql(f"UPDATE {reference} SET asset_name='BTC test' WHERE symbol='BTCUSDT'")
        dbt('snapshot')
        expect(f"SELECT COUNT(*) FROM {snapshot} WHERE symbol='BTCUSDT'", 2)
        expect(f"SELECT COUNT(*) FROM {snapshot} WHERE symbol='BTCUSDT' AND dbt_valid_to IS NULL", 1)
        sql(f"DELETE FROM {reference} WHERE symbol='SOLUSDT'")
        dbt('snapshot')
        expect(f"SELECT COUNT(*) FROM {snapshot} WHERE symbol='SOLUSDT' AND dbt_valid_to IS NULL", 0)
        # Restore seed before tests; this also tests reappearance of a deleted entity.
        dbt('seed')
        dbt('snapshot')
        dbt('run')
        dbt('test')
        # Force a hook failure AFTER its audit insert: both insert and model UPDATE
        # must roll back. Only the disposable model text and fixture are changed.
        before = sql(f'SELECT COUNT(*) FROM {audit}')[0][0]
        model = project / 'models/staging/stg_crypto_prices.sql'
        model.write_text(model.read_text(encoding='utf-8').replace(
            'post_hook=["{{ audit_model_success() }}"]',
            'post_hook=["{{ audit_model_success() }}", "SELECT 1/0"]'), encoding='utf-8')
        sql(f"UPDATE {fixtures} SET price=999 WHERE record_id='a'")
        dbt('run', '--select', 'stg_crypto_prices', fails=True)
        expect(f'SELECT COUNT(*) FROM {audit}', before)
        expect(f"SELECT price FROM {staging} WHERE record_id='a'", 105)
        print('PASS: Redshift incremental/snapshot/audit lifecycle and rollback', flush=True)
    finally:
        # Names are generated above, never supplied by a user. Drop only our schemas.
        try:
            for suffix in ('_gold', '_intermediate', '_staging', '_reference', '_snapshots',
                           '_fixtures', ''):
                sql(f'DROP SCHEMA IF EXISTS {schema}{suffix} CASCADE')
        finally:
            connection.close()
        print(f'Cleanup attempted for {schema}; local artifacts: {project}', flush=True)


if __name__ == '__main__':
    main()
