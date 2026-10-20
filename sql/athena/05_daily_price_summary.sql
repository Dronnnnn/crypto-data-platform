-- Example analytical aggregate over Silver. Keep the partition filters when
-- adapting this query to a narrow reporting period to reduce data scanned.
SELECT
    source,
    ingest_date,
    symbol,
    MIN(price) AS min_price,
    MAX(price) AS max_price,
    AVG(price) AS average_price,
    COUNT(*) AS record_count
FROM crypto_data_lake.silver_crypto_prices
WHERE source = 'binance'
  AND ingest_date = DATE '${RUN_DATE}'
GROUP BY source, ingest_date, symbol
ORDER BY ingest_date, symbol;
