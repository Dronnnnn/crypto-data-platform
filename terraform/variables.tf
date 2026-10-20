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

variable "redshift_namespace_name" {
  description = "Redshift Serverless namespace name"
  type        = string
  default     = "crypto-data-platform"
}

variable "redshift_workgroup_name" {
  description = "Redshift Serverless workgroup name"
  type        = string
  default     = "crypto-data-platform"
}

variable "redshift_database_name" {
  description = "Initial database created in the Redshift Serverless namespace"
  type        = string
  default     = "crypto_warehouse"
}

variable "redshift_admin_username" {
  description = "Administrator username for the Redshift Serverless namespace"
  type        = string
  default     = "adminuser"
}

variable "redshift_base_capacity" {
  description = "Redshift Processing Units (RPUs) allocated to the Serverless workgroup"
  type        = number
  default     = 8
}

variable "redshift_port" {
  description = "TCP port used by the Redshift Serverless endpoint"
  type        = number
  default     = 5439
}

variable "redshift_publicly_accessible" {
  description = "Whether the Redshift endpoint may be reached from the public internet"
  type        = bool
  default     = false
}

variable "redshift_allowed_cidr" {
  description = "Single trusted client CIDR allowed to reach Redshift when public access is explicitly enabled"
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = !var.redshift_publicly_accessible || var.redshift_allowed_cidr != null
    error_message = "Set redshift_allowed_cidr when redshift_publicly_accessible is true."
  }

  validation {
    condition = var.redshift_allowed_cidr == null ? true : (
      can(cidrnetmask(var.redshift_allowed_cidr)) &&
      can(regex("/32$", var.redshift_allowed_cidr)) &&
      var.redshift_allowed_cidr != "0.0.0.0/32"
    )
    error_message = "Only a single trusted IPv4 client address (/32) is allowed; broad networks are forbidden."
  }
}
