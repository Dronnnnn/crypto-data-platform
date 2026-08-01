output "bucket_name" {
  description = "S3 Bucket name"
  value       = aws_s3_bucket.data_lake.bucket
}

output "bucket_arn" {
  description = "S3 Bucket ARN"
  value       = aws_s3_bucket.data_lake.arn
}

output "glue_database_name" {
  description = "Glue Data Catalog database containing the Silver table"
  value       = aws_glue_catalog_database.crypto_data_lake.name
}

output "silver_crypto_prices_table_name" {
  description = "Glue Data Catalog table backed by Silver Parquet files"
  value       = aws_glue_catalog_table.silver_crypto_prices.name
}

output "athena_workgroup_name" {
  description = "Athena workgroup configured for this data platform"
  value       = aws_athena_workgroup.data_platform.name
}

output "athena_results_location" {
  description = "S3 prefix used by Athena to store query results"
  value       = "s3://${local.data_lake_bucket_name}/athena-results/"
}

output "athena_silver_analyst_policy_arn" {
  description = "IAM policy to attach to an analyst role or group when least-privilege Athena access is needed"
  value       = aws_iam_policy.athena_silver_analyst.arn
}
