import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from crypto_data_platform.common.config import settings
from crypto_data_platform.common.exceptions import StorageError
from crypto_data_platform.common.logger import get_logger
from crypto_data_platform.models.price import Price

logger = get_logger(__name__)

RAW_DATA_DIR = Path(settings.raw_data_path)


def save_json(data: Price) -> Path:
    """
    Save API response to local JSON file.
    """

    symbol = data.symbol

    logger.info(
        "Saving data for %s",
        symbol,
    )

    try:
        RAW_DATA_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        file_path = RAW_DATA_DIR / f"{symbol.lower()}_{timestamp}.json"

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
        raise StorageError(f"Failed to save file {file_path}") from error
