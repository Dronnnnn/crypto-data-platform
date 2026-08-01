-- Read one Silver partition. Filtering by both partition columns allows Athena
-- to skip Parquet files belonging to other sources and ingestion dates.
SELECT
    record_id,
    source,
    ingest_date,
    symbol,
    price,
    bronze_loaded_at,
    silver_loaded_at
FROM crypto_data_lake.silver_crypto_prices
WHERE source = 'binance'
  AND ingest_date = DATE '2026-07-29'
ORDER BY silver_loaded_at DESC;
