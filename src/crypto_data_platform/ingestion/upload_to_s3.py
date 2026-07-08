from crypto_data_platform.common.aws import get_s3_client
from crypto_data_platform.common.config import settings
from crypto_data_platform.common.logger import get_logger

logger = get_logger(__name__)


def upload_file(
    file_path: str,
    s3_key: str,
):
    client = get_s3_client()

    logger.info(
        "Uploading %s to s3://%s/%s",
        file_path,
        settings.s3_bucket,
        s3_key,
    )

    client.upload_file(
        file_path,
        settings.s3_bucket,
        s3_key,
    )

    logger.info("Upload completed")


if __name__ == "__main__":
    upload_file(
        "data/test.json",
        "raw/test.json",
    )
