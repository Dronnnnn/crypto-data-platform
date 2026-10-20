WITH ranked AS (
    SELECT source, symbol, record_id, price,
           ROW_NUMBER() OVER (
               PARTITION BY source, symbol ORDER BY bronze_loaded_at DESC, record_id DESC
           ) AS rn
    FROM {{ ref('stg_crypto_prices') }}
), expected AS (
    SELECT * FROM ranked WHERE rn = 1
)
SELECT COALESCE(e.symbol, a.symbol) AS symbol
FROM expected e
FULL OUTER JOIN {{ ref('gold_latest_crypto_price') }} a
  ON e.source = a.source AND e.symbol = a.symbol
WHERE e.record_id IS NULL OR a.record_id IS NULL OR e.record_id <> a.record_id
   OR a.latest_price IS NULL OR e.price <> a.latest_price
