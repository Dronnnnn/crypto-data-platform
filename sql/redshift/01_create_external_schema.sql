-- Run this while connected to the Redshift database crypto_warehouse.
-- Terraform attaches crypto-data-platform-redshift-spectrum as the namespace's
-- default IAM role, so no ARN needs to be copied into this versioned SQL file.
-- This creates a logical reference to Glue Catalog; it does not copy Parquet
-- data from S3 into Redshift.
CREATE EXTERNAL SCHEMA IF NOT EXISTS spectrum_silver
FROM DATA CATALOG
DATABASE 'crypto_data_lake'
REGION 'ap-southeast-1'
IAM_ROLE default;
