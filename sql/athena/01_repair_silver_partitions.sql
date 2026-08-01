-- Discover Hive-style S3 directories created by Spark and register them as
-- Glue Catalog partitions. Run after new Silver data has been written.
MSCK REPAIR TABLE crypto_data_lake.silver_crypto_prices;
