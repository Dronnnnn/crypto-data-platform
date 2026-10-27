-- Rebuilding processing timestamps must not make an older ingestion day "latest".
WITH expected AS (
    SELECT source, symbol, MAX(ingest_date) AS latest_ingest_date
    FROM {{ ref('stg_crypto_prices') }}
    GROUP BY source, symbol
)
SELECT e.source, e.symbol, e.latest_ingest_date, a.ingest_date
FROM expected e
LEFT JOIN {{ ref('gold_latest_crypto_price') }} a
    ON e.source = a.source AND e.symbol = a.symbol
WHERE a.ingest_date IS NULL OR a.ingest_date <> e.latest_ingest_date
