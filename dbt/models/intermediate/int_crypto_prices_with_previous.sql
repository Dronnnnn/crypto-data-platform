{{ config(materialized='view') }}

WITH priced AS (
    SELECT
        *,
        LAG(price) OVER (
            PARTITION BY source, symbol
            ORDER BY bronze_loaded_at, record_id
        ) AS previous_price
    FROM {{ ref('stg_crypto_prices') }}
)

SELECT
    record_id,
    source,
    ingest_date,
    symbol,
    price,
    previous_price,
    price - previous_price AS price_change,
    CASE
        WHEN previous_price IS NULL OR previous_price = 0 THEN NULL
        ELSE ((price - previous_price) / previous_price) * 100
    END AS price_change_percent,
    bronze_loaded_at,
    silver_loaded_at,
    base_asset,
    quote_asset,
    asset_name
FROM priced
