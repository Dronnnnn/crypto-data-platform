resource "aws_redshiftserverless_namespace" "warehouse" {
  namespace_name        = var.redshift_namespace_name
  db_name               = var.redshift_database_name
  admin_username        = var.redshift_admin_username
  manage_admin_password = true

  # Spectrum uses this role to read Glue metadata and only Silver objects in S3.
  default_iam_role_arn = aws_iam_role.redshift_spectrum.arn
  iam_roles            = [aws_iam_role.redshift_spectrum.arn]
  log_exports          = ["userlog", "connectionlog", "useractivitylog"]

  tags = local.common_tags
}

resource "aws_redshiftserverless_workgroup" "warehouse" {
  workgroup_name      = var.redshift_workgroup_name
  namespace_name      = aws_redshiftserverless_namespace.warehouse.namespace_name
  base_capacity       = var.redshift_base_capacity
  publicly_accessible = var.redshift_publicly_accessible
  port                = var.redshift_port
  security_group_ids  = [aws_security_group.redshift_serverless.id]
  subnet_ids          = data.aws_subnets.default.ids

  tags = local.common_tags
}
