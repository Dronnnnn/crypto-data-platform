-- Read a narrow external-table partition through Redshift Spectrum. Filtering
-- by both partition columns limits the S3 files Spectrum needs to scan.
SELECT
    record_id,
    source,
    ingest_date,
    symbol,
    price,
    bronze_loaded_at,
    silver_loaded_at
FROM spectrum_silver.silver_crypto_prices
WHERE source = 'binance'
  AND ingest_date = DATE '2026-07-29'
ORDER BY bronze_loaded_at, record_id;
