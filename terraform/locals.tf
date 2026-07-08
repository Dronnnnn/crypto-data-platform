locals {
  project_name = "crypto-data-platform"

  name_prefix = local.project_name

  common_tags = {
    Project     = local.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}