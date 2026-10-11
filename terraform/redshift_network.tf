# This project has no VPC managed in Terraform yet. The workgroup uses the
# account's default VPC and its default subnets, discovered at plan/apply time.
# It remains private unless redshift_publicly_accessible is explicitly enabled.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

resource "aws_security_group" "redshift_serverless" {
  name        = "${local.name_prefix}-redshift-serverless"
  description = "Network access controls for the Redshift Serverless workgroup"
  vpc_id      = data.aws_vpc.default.id

  dynamic "ingress" {
    for_each = var.redshift_publicly_accessible ? [var.redshift_allowed_cidr] : []

    content {
      description = "Redshift SQL access from the explicitly trusted client CIDR"
      from_port   = var.redshift_port
      to_port     = var.redshift_port
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    description = "HTTPS to AWS service endpoints"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-redshift-serverless" })
}
