from datetime import UTC, datetime

from crypto_data_platform.common.config import settings


def build_file_name(
    symbol: str,
    ingest_time: datetime,
) -> str:
    """
    Build JSON filename.
    """

    return f"{symbol.lower()}_" f"{ingest_time.astimezone(UTC):%Y%m%d_%H%M%S}.json"


def build_s3_key(
    source: str,
    symbol: str,
    ingest_time: datetime,
) -> str:
    """
    Build partitioned S3 key.

    Example:

    raw/source=binance/symbol=BTCUSDT/ingest_date=2026-07-19/file.json
    """

    return "/".join(
        (
            settings.s3_raw_prefix.strip("/"),
            f"source={source}",
            f"symbol={symbol.upper()}",
            f"ingest_date={ingest_time.astimezone(UTC):%Y-%m-%d}",
            build_file_name(symbol, ingest_time),
        )
    )
