import boto3

from crypto_data_platform.common.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
    )
