import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from crypto_data_platform.common.config import settings
from crypto_data_platform.common.exceptions import StorageError
from crypto_data_platform.common.logger import get_logger
from crypto_data_platform.common.path_builder import build_local_file_path
from crypto_data_platform.models.price import Price

logger = get_logger(__name__)

RAW_DATA_DIR = Path(settings.raw_data_path)


def save_json(
    data: Price,
    source: str,
) -> Path:
    """
    Save API response to local JSON file.
    """

    symbol = data.symbol

    logger.info(
        "Saving data for %s",
        symbol,
    )

    try:
        ingest_time = datetime.now(UTC)

        file_path = build_local_file_path(
            source,
            data.symbol,
            ingest_time,
        )

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                asdict(data),
                file,
                indent=4,
                ensure_ascii=False,
            )

        logger.info(
            "Saved file %s",
            file_path,
        )

        return file_path

    except OSError as error:
        logger.exception("Failed to save file")

        raise StorageError("Failed to save file") from error
