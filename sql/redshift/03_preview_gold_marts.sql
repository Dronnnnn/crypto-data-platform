-- Run after dbt seed, run, and test have completed successfully.
SELECT *
FROM analytics_gold.gold_latest_crypto_price
ORDER BY source, symbol;

SELECT *
FROM analytics_gold.gold_daily_crypto_price_summary
ORDER BY ingest_date, source, symbol;

-- Both counts must be positive after the selected DAG run.
SELECT COUNT(*) AS latest_rows_for_run_date
FROM analytics_gold.gold_latest_crypto_price
WHERE ingest_date = DATE '${RUN_DATE}';

SELECT COUNT(*) AS daily_rows_for_run_date, SUM(price_record_count) AS observations
FROM analytics_gold.gold_daily_crypto_price_summary
WHERE ingest_date = DATE '${RUN_DATE}';
