-- One open version per symbol, nonempty intervals, no overlapping versions.
WITH versions AS (
    SELECT *, LEAD(dbt_valid_from) OVER (
        PARTITION BY symbol ORDER BY dbt_valid_from, dbt_scd_id
    ) AS next_valid_from
    FROM {{ ref('crypto_symbols_snapshot') }}
)
SELECT symbol FROM versions
WHERE (dbt_valid_to IS NOT NULL AND dbt_valid_to <= dbt_valid_from)
   OR (next_valid_from IS NOT NULL AND
       (dbt_valid_to IS NULL OR dbt_valid_to > next_valid_from))
UNION ALL
SELECT symbol FROM versions
WHERE dbt_valid_to IS NULL
GROUP BY symbol HAVING COUNT(*) > 1
