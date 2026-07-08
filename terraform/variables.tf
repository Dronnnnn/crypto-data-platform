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