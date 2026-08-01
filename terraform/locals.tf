locals {
  project_name = "crypto-data-platform"

  name_prefix = local.project_name

  # By default Athena and Glue use the bucket managed by this Terraform state.
  # The variable makes it possible to point the catalog at an existing bucket
  # when this configuration is reused in another environment.
  data_lake_bucket_name = coalesce(var.data_lake_bucket_name, aws_s3_bucket.data_lake.bucket)

  common_tags = {
    Project     = local.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
