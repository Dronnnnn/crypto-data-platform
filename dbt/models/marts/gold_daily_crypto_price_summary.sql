{{ config(materialized='table') }}

SELECT
    MD5(source || '|' || CAST(ingest_date AS VARCHAR) || '|' || symbol) AS daily_price_key,
    source,
    ingest_date,
    symbol,
    MIN(price) AS min_price,
    MAX(price) AS max_price,
    AVG(price) AS average_price,
    COUNT(*) AS price_record_count,
    MIN(bronze_loaded_at) AS first_bronze_loaded_at,
    MAX(bronze_loaded_at) AS last_bronze_loaded_at
FROM {{ ref('stg_crypto_prices') }}
GROUP BY source, ingest_date, symbol
