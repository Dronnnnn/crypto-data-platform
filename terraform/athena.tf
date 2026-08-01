resource "aws_athena_workgroup" "data_platform" {
  name          = var.athena_workgroup_name
  description   = "Athena queries for the ${local.project_name} data lake"
  force_destroy = false

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${local.data_lake_bucket_name}/athena-results/"
    }
  }

  tags = local.common_tags
}
