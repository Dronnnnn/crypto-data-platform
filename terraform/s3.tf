resource "aws_s3_bucket" "data_lake" {
  bucket_prefix = "crypto-data-platform-raw-"

  tags = {
    Project     = "crypto-data-platform"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}