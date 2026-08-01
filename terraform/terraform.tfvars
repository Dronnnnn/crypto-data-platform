# Copy this file to terraform.tfvars only when you need to override defaults.
# terraform.tfvars is ignored by Git and must not contain credentials.

aws_region  = "ap-southeast-1"
environment = "dev"

# Leave null to use the S3 bucket managed by this Terraform state.
# Set a real name only when reusing the catalog configuration with another bucket.
data_lake_bucket_name = null

glue_database_name              = "crypto_data_lake"
silver_crypto_prices_table_name = "silver_crypto_prices"
athena_workgroup_name           = "crypto-data-platform"
