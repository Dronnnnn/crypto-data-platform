-- Full outer join catches missing and extra groups as well as wrong aggregates.
WITH expected AS (
    SELECT source, ingest_date, symbol, COUNT(*) AS n,
           MIN(price) AS lo, MAX(price) AS hi, AVG(price) AS mean_price
    FROM {{ ref('stg_crypto_prices') }}
    GROUP BY source, ingest_date, symbol
)
SELECT COALESCE(e.symbol, a.symbol) AS symbol
FROM expected e
FULL OUTER JOIN {{ ref('gold_daily_crypto_price_summary') }} a
  ON e.source = a.source AND e.ingest_date = a.ingest_date AND e.symbol = a.symbol
WHERE e.n IS NULL OR a.daily_price_key IS NULL
   OR a.price_record_count IS NULL OR a.price_record_count <> e.n
   OR a.min_price IS NULL OR a.min_price <> e.lo
   OR a.max_price IS NULL OR a.max_price <> e.hi
   OR a.average_price IS NULL OR ABS(a.average_price - e.mean_price) > 0.00000001
