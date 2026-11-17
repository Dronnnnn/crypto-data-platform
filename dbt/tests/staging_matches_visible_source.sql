-- Detect missed late rows, corrections, and seed enrichment changes.
SELECT prices.record_id, prices.source, prices.ingest_date, prices.symbol,
       CAST(prices.price AS NUMERIC(20, 8)) AS price,
       prices.bronze_loaded_at, prices.silver_loaded_at,
       symbols.base_asset, symbols.quote_asset, symbols.asset_name
FROM {{ source('spectrum_silver', 'silver_crypto_prices') }} AS prices
LEFT JOIN {{ ref('crypto_symbols') }} AS symbols ON prices.symbol = symbols.symbol
EXCEPT
SELECT record_id, source, ingest_date, symbol, price,
       bronze_loaded_at, silver_loaded_at, base_asset, quote_asset, asset_name
FROM {{ ref('stg_crypto_prices') }}
