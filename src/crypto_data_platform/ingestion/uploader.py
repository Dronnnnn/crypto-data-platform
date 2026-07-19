from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError

from crypto_data_platform.common.aws import get_s3_client
from crypto_data_platform.common.config import settings
from crypto_data_platform.common.exceptions import UploadError
from crypto_data_platform.common.logger import get_logger

logger = get_logger(__name__)


def upload_file(
    file_path: Path,
    prefix: str,
) -> None:
    """
    Upload file to S3 bucket.
    """

    s3_key = f"{prefix}/{file_path.name}"

    logger.info(
        "Uploading %s to s3://%s/%s",
        file_path,
        settings.s3_bucket,
        s3_key,
    )

    client = get_s3_client()

    try:
        client.upload_file(
            str(file_path),
            settings.s3_bucket,
            s3_key,
        )

    except (ClientError, BotoCoreError) as error:
        raise UploadError(f"Failed to upload {file_path.name}") from error

    logger.info("Upload completed")
