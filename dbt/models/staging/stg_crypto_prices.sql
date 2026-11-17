{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='record_id',
    on_schema_change='fail',
    pre_hook="{{ create_model_audit_table() }}",
    post_hook=["{{ audit_model_success() }}"]
) }}

-- This table is deliberately thin: Redshift cannot build a regular view directly
-- on a Spectrum external table. It standardizes and persists the external source
-- before reusable calculations and Gold marts are built in Redshift.
WITH candidates AS (
SELECT
    prices.record_id,
    prices.source,
    prices.ingest_date,
    prices.symbol,
    CAST(prices.price AS NUMERIC(20, 8)) AS price,
    prices.bronze_loaded_at,
    prices.silver_loaded_at,
    symbols.base_asset,
    symbols.quote_asset,
    symbols.asset_name
FROM {{ source('spectrum_silver', 'silver_crypto_prices') }} AS prices
LEFT JOIN {{ ref('crypto_symbols') }} AS symbols
    ON prices.symbol = symbols.symbol
WHERE prices.record_id IS NOT NULL
  AND prices.symbol IS NOT NULL
  AND prices.price > 0
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY record_id
        ORDER BY silver_loaded_at DESC, bronze_loaded_at DESC,
                 source, ingest_date, symbol, price, base_asset, quote_asset, asset_name
    ) AS record_rank
    FROM candidates
), current_rows AS (
    SELECT record_id, source, ingest_date, symbol, price,
           bronze_loaded_at, silver_loaded_at, base_asset, quote_asset, asset_name
    FROM ranked
    WHERE record_rank = 1
)
SELECT * FROM current_rows
{% if is_incremental() %}
-- Compare the complete visible source, including old partitions. EXCEPT is
-- NULL-safe and includes enrichment corrections and rebuilt processing times.
-- No ingestion-date/timestamp watermark: late records must not be skipped.
EXCEPT
SELECT record_id, source, ingest_date, symbol, price,
       bronze_loaded_at, silver_loaded_at, base_asset, quote_asset, asset_name
FROM {{ this }}
{% endif %}
