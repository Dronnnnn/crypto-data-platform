data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "athena_silver_analyst" {
  statement {
    sid = "ListDataLakeBucket"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = ["arn:aws:s3:::${local.data_lake_bucket_name}"]
  }

  statement {
    sid       = "ReadSilverParquet"
    actions   = ["s3:GetObject"]
    resources = ["arn:aws:s3:::${local.data_lake_bucket_name}/silver/*"]
  }

  statement {
    sid = "ManageAthenaQueryResults"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]

    resources = ["arn:aws:s3:::${local.data_lake_bucket_name}/athena-results/*"]
  }

  statement {
    sid = "ReadGlueCatalogMetadata"

    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetPartition",
      "glue:GetPartitions",
    ]

    resources = [
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:database/${var.glue_database_name}",
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.glue_database_name}/${var.silver_crypto_prices_table_name}",
    ]
  }

  statement {
    sid       = "StartQueriesInProjectWorkgroup"
    actions   = ["athena:StartQueryExecution"]
    resources = [aws_athena_workgroup.data_platform.arn]
  }

  # Athena query-execution resources are not individually addressable in IAM,
  # so status actions require Resource = "*".
  statement {
    sid = "InspectAthenaQueries"

    actions = [
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:ListQueryExecutions",
      "athena:StopQueryExecution",
    ]

    resources = ["*"]
  }
}

# The policy is intentionally not attached here. Attach its ARN to the IAM role
# or group used by analysts; this keeps identity management outside this project.
resource "aws_iam_policy" "athena_silver_analyst" {
  name        = "${local.name_prefix}-athena-silver-analyst"
  description = "Least-privilege access to query the Silver data lake with Athena"
  policy      = data.aws_iam_policy_document.athena_silver_analyst.json

  tags = local.common_tags
}
