variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "data_lake_bucket_name" {
  description = "Existing S3 data lake bucket name. When null, use the bucket managed by this Terraform state."
  type        = string
  default     = null
  nullable    = true
}

variable "glue_database_name" {
  description = "Glue Data Catalog database for data lake tables"
  type        = string
  default     = "crypto_data_lake"
}

variable "silver_crypto_prices_table_name" {
  description = "Glue table name for the canonical Silver crypto price dataset"
  type        = string
  default     = "silver_crypto_prices"
}

variable "athena_workgroup_name" {
  description = "Dedicated Athena workgroup for this project"
  type        = string
  default     = "crypto-data-platform"
}
