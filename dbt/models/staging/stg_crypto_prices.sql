{{ config(materialized='table') }}

-- This table is deliberately thin: Redshift cannot build a regular view directly
-- on a Spectrum external table. It standardizes and persists the external source
-- before reusable calculations and Gold marts are built in Redshift.
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
