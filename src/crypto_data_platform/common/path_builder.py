from datetime import UTC, datetime
from pathlib import Path

from crypto_data_platform.common.config import settings


def build_partition_path(
    source: str,
    symbol: str,
    ingest_time: datetime,
) -> Path:
    """
    Build partitioned path for local storage.

    Example:
    data/raw/source=binance/symbol=BTCUSDT/ingest_date=2026-07-19/
    """

    return (
        Path(settings.raw_data_path)
        / f"source={source}"
        / f"symbol={symbol}"
        / f"ingest_date={ingest_time:%Y-%m-%d}"
    )


def build_file_name(
    symbol: str,
    ingest_time: datetime,
) -> str:
    """
    Build JSON filename.
    """

    return f"{symbol.lower()}_" f"{ingest_time.astimezone(UTC):%Y%m%d_%H%M%S}.json"


def build_local_file_path(
    source: str,
    symbol: str,
    ingest_time: datetime,
) -> Path:
    """
    Build complete local file path.
    """

    return build_partition_path(
        source,
        symbol,
        ingest_time,
    ) / build_file_name(symbol, ingest_time)


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

    return str(
        Path(settings.s3_raw_prefix)
        / build_partition_path(
            source,
            symbol,
            ingest_time,
        ).relative_to(settings.raw_data_path)
        / build_file_name(symbol, ingest_time)
    ).replace("\\", "/")
