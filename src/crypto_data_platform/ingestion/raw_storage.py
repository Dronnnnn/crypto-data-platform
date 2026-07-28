import json
from datetime import UTC, datetime
from typing import Any

from crypto_data_platform.common.config import settings
from crypto_data_platform.common.exceptions import UploadError
from crypto_data_platform.common.logger import get_logger
from crypto_data_platform.common.path_builder import build_s3_key
from crypto_data_platform.common.s3 import get_s3_client

logger = get_logger(__name__)


def upload_raw_json(
    payload: dict[str, Any],
    source: str,
    symbol: str,
    ingest_time: datetime | None = None,
) -> str:
    """
    Upload original API response to Raw layer in S3.
    """

    ingest_time = ingest_time or datetime.now(UTC)

    key = build_s3_key(
        source=source,
        symbol=symbol,
        ingest_time=ingest_time,
    )

    logger.info("Uploading raw payload to s3://%s/%s", settings.s3_bucket, key)

    try:
        client = get_s3_client()

        client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8"),
            ContentType="application/json",
            Metadata={
                "source": source,
                "symbol": symbol.upper(),
                "ingested-at": ingest_time.astimezone(UTC).isoformat(),
                "schema-version": "1",
            },
        )

        logger.info("Upload completed")

        return key

    except Exception as error:
        logger.exception("Failed to upload raw payload")

        raise UploadError("Failed to upload raw payload") from error
