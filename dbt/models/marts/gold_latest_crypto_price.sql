{{ config(materialized='table') }}

WITH ranked_prices AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY source, symbol
            ORDER BY bronze_loaded_at DESC, record_id DESC
        ) AS price_rank
    FROM {{ ref('int_crypto_prices_with_previous') }}
)

SELECT
    MD5(source || '|' || symbol) AS latest_price_key,
    record_id,
    source,
    symbol,
    price AS latest_price,
    previous_price,
    price_change,
    price_change_percent,
    bronze_loaded_at AS observed_at,
    ingest_date,
    base_asset,
    quote_asset,
    asset_name
FROM ranked_prices
WHERE price_rank = 1
