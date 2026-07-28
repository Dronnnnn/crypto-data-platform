from typing import Any

import requests

from crypto_data_platform.common.config import settings
from crypto_data_platform.common.exceptions import APIError
from crypto_data_platform.common.logger import get_logger
from crypto_data_platform.common.retry import sleep_before_retry

logger = get_logger(__name__)


def fetch_price(symbol: str) -> dict[str, Any]:
    """
    Fetch current symbol price from Binance API.
    """

    url = f"{settings.binance_base_url}/api/v3/ticker/price"

    for attempt in range(1, settings.max_retries + 1):
        try:
            response = requests.get(
                url,
                params={"symbol": symbol},
                timeout=settings.request_timeout,
            )

            response.raise_for_status()

            logger.info(
                "Fetched price for %s",
                symbol,
            )

            return response.json()

        except requests.exceptions.RequestException as error:
            logger.warning(
                "Attempt %s/%s failed: %s",
                attempt,
                settings.max_retries,
                error,
            )

            if attempt == settings.max_retries:
                raise APIError(f"Failed to fetch price for {symbol}.") from error

            sleep_before_retry(attempt)
