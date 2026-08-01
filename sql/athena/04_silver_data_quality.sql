-- Silver quality checks. A result count greater than zero indicates a problem.
-- record_id is a SHA-256 hash of raw_file_path. It is a stable technical key
-- for one landed Raw object and does not expose the physical S3 path.
WITH invalid_prices AS (
    SELECT 'non_positive_price' AS check_name, COUNT(*) AS invalid_record_count
    FROM crypto_data_lake.silver_crypto_prices
    WHERE price <= 0
),
null_required_fields AS (
    SELECT 'null_required_field' AS check_name, COUNT(*) AS invalid_record_count
    FROM crypto_data_lake.silver_crypto_prices
    WHERE record_id IS NULL
       OR source IS NULL
       OR symbol IS NULL
       OR price IS NULL
       OR ingest_date IS NULL
       OR bronze_loaded_at IS NULL
       OR silver_loaded_at IS NULL
),
duplicate_keys AS (
    SELECT record_id, COUNT(*) AS records_with_same_id
    FROM crypto_data_lake.silver_crypto_prices
    GROUP BY record_id
    HAVING COUNT(*) > 1
),
duplicates AS (
    SELECT 'duplicate_record_id' AS check_name,
           COALESCE(SUM(records_with_same_id - 1), 0) AS invalid_record_count
    FROM duplicate_keys
)
SELECT * FROM invalid_prices
UNION ALL
SELECT * FROM null_required_fields
UNION ALL
SELECT * FROM duplicates;
