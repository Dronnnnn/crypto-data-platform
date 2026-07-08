output "bucket_name" {
  description = "S3 Bucket name"
  value       = aws_s3_bucket.data_lake.bucket
}

output "bucket_arn" {
  description = "S3 Bucket ARN"
  value       = aws_s3_bucket.data_lake.arn
}