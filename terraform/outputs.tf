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

output "redshift_database_name" {
  description = "Initial database in the Redshift Serverless namespace"
  value       = aws_redshiftserverless_namespace.warehouse.db_name
}

output "redshift_workgroup_name" {
  description = "Redshift Serverless workgroup name"
  value       = aws_redshiftserverless_workgroup.warehouse.workgroup_name
}

output "redshift_endpoint_host" {
  description = "Redshift Serverless endpoint hostname"
  value       = aws_redshiftserverless_workgroup.warehouse.endpoint[0].address
}

output "redshift_namespace_name" {
  value = aws_redshiftserverless_namespace.warehouse.namespace_name
}

output "catalog_bucket_name" {
  description = "Bucket actually used by Glue/Spectrum and the ingestion walkthrough"
  value       = local.data_lake_bucket_name
}

output "redshift_endpoint_port" {
  description = "Redshift Serverless endpoint port"
  value       = aws_redshiftserverless_workgroup.warehouse.endpoint[0].port
}

output "redshift_spectrum_role_arn" {
  description = "IAM role attached to Redshift for Spectrum reads of Silver"
  value       = aws_iam_role.redshift_spectrum.arn
}
