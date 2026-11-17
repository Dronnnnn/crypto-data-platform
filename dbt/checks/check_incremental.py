"""Execute the actual model SELECT locally; not a Redshift adapter integration test."""
import sqlite3
from pathlib import Path

from jinja2 import Environment, StrictUndefined


MODEL = Path('dbt/models/staging/stg_crypto_prices.sql').read_text(encoding='utf-8')


def render(incremental):
    return Environment(undefined=StrictUndefined).from_string(MODEL).render(
        config=lambda **kwargs: '',
        source=lambda *args: 'silver',
        ref=lambda name: name,
        is_incremental=lambda: incremental,
        this='staging',
    )


def test_incremental_lifecycle():
    db = sqlite3.connect(':memory:')
    db.executescript('''
        CREATE TABLE silver (record_id TEXT, source TEXT, ingest_date TEXT,
          symbol TEXT, price NUMERIC, bronze_loaded_at TEXT, silver_loaded_at TEXT);
        CREATE TABLE crypto_symbols (symbol TEXT, base_asset TEXT, quote_asset TEXT,
          asset_name TEXT);
        INSERT INTO crypto_symbols VALUES ('BTCUSDT','BTC','USDT','Bitcoin');
        INSERT INTO silver VALUES ('a','binance','2026-11-17','BTCUSDT',100,'t1','t1');
    ''')

    def run(full=False):
        if full:
            db.execute('DROP TABLE IF EXISTS staging')
            db.execute('CREATE TABLE staging AS ' + render(False))
        else:
            db.execute('CREATE TEMP TABLE delta AS ' + render(True))
            db.execute('DELETE FROM staging WHERE record_id IN (SELECT record_id FROM delta)')
            db.execute('INSERT INTO staging SELECT * FROM delta')
            db.execute('DROP TABLE delta')
        assert db.execute('SELECT COUNT(*) = COUNT(DISTINCT record_id) FROM staging').fetchone()[0]

    run(full=True)
    assert db.execute('SELECT COUNT(*) FROM staging').fetchone()[0] == 1
    assert db.execute(render(True)).fetchall() == []
    run()
    db.executescript('''
        INSERT INTO silver VALUES ('b','binance','2026-11-18','BTCUSDT',110,'t2','t2');
        INSERT INTO silver VALUES ('late','binance','2020-01-01','BTCUSDT',90,'t0','t0');
        UPDATE silver SET price=105 WHERE record_id='a';
    ''')
    run()
    assert db.execute('SELECT COUNT(*) FROM staging').fetchone()[0] == 3
    assert db.execute("SELECT price FROM staging WHERE record_id='a'").fetchone()[0] == 105
    db.execute("UPDATE silver SET bronze_loaded_at='t3',silver_loaded_at='t3'")
    run()
    assert db.execute("SELECT COUNT(*) FROM staging WHERE silver_loaded_at='t3'").fetchone()[0] == 3
    db.execute("UPDATE crypto_symbols SET asset_name=NULL")
    run()
    assert db.execute('SELECT COUNT(*) FROM staging WHERE asset_name IS NULL').fetchone()[0] == 3
    assert db.execute(render(True)).fetchall() == []
    # Duplicate input cannot multiply target keys; source uniqueness test still fails.
    db.execute("INSERT INTO silver SELECT * FROM silver WHERE record_id='b'")
    run()
    db.execute("DELETE FROM silver WHERE record_id='late'")
    run()
    assert db.execute('SELECT COUNT(*) FROM staging').fetchone()[0] == 3
    run(full=True)
    assert db.execute('SELECT COUNT(*) FROM staging').fetchone()[0] == 2
    db.close()


if __name__ == '__main__':
    test_incremental_lifecycle()
    print('PASS: local incremental SELECT lifecycle (SQLite; not Redshift)')
