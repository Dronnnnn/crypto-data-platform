resource "aws_s3_bucket" "data_lake" {
  bucket_prefix = "${local.project_name}-raw-"

  tags = local.common_tags
}