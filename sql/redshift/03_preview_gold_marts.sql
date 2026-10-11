-- Run after dbt seed, run, and test have completed successfully.
SELECT *
FROM analytics_gold.gold_latest_crypto_price
ORDER BY source, symbol;

SELECT *
FROM analytics_gold.gold_daily_crypto_price_summary
ORDER BY ingest_date, source, symbol;
