import json
from datetime import UTC, datetime
from pathlib import Path

from crypto_data_platform.common.logger import get_logger

logger = get_logger(__name__)

RAW_DATA_DIR = Path("data/raw")


def save_json(data: dict) -> Path:
    """
    Save API response as JSON file.

    Returns path to created file.
    """
    symbol = data["symbol"]
    logger.info("Saving data for %s", symbol)

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    filename = f"{symbol.lower()}_{timestamp}.json"

    file_path = RAW_DATA_DIR / filename

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )

    logger.info("Saved file %s", file_path)

    return file_path
