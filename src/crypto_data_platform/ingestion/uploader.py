from pathlib import Path

from crypto_data_platform.common.aws import get_s3_client
from crypto_data_platform.common.config import settings
from crypto_data_platform.common.logger import get_logger

logger = get_logger(__name__)


def upload_file(file_path: Path, prefix: str = 'raw') -> None:
    """
    Upload local file to S3.
    """

    client = get_s3_client()
    s3_key = f"{prefix}/{file_path.name}"

    logger.info(
        "Uploading %s to s3://%s/%s",
        file_path,
        settings.s3_bucket,
        s3_key,
    )

    client.upload_file(
        str(file_path),
        settings.s3_bucket,
        s3_key,
    )

    logger.info("Upload completed")