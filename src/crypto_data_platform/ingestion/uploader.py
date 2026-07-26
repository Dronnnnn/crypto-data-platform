from pathlib import Path

from crypto_data_platform.common.aws import get_s3_client
from crypto_data_platform.common.config import settings
from crypto_data_platform.common.exceptions import UploadError
from crypto_data_platform.common.logger import get_logger

logger = get_logger(__name__)


def upload_file(file_path: Path) -> None:
    """
    Upload local file to S3.
    """

    client = get_s3_client()

    relative_path = file_path.relative_to(settings.raw_data_path)

    s3_key = f"{settings.s3_raw_prefix}/{relative_path.as_posix()}"

    logger.info(
        "Uploading %s to s3://%s/%s",
        file_path,
        settings.s3_bucket,
        s3_key,
    )

    try:
        client.upload_file(
            str(file_path),
            settings.s3_bucket,
            s3_key,
        )

    except Exception as error:
        raise UploadError(
            f"Failed to upload {file_path.name}"
        ) from error

    logger.info("Upload completed")