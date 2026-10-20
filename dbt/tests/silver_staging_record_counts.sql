-- Defensive staging filters must not silently hide invalid source rows.
SELECT 'silver_staging_row_count_mismatch' AS failure
WHERE (SELECT COUNT(*) FROM {{ source('spectrum_silver', 'silver_crypto_prices') }})
   <> (SELECT COUNT(*) FROM {{ ref('stg_crypto_prices') }})
