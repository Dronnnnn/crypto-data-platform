import requests

from crypto_data_platform.common.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.binance.com"


def fetch_symbol_price(symbol: str) -> dict:
    """
    Fetch current symbol price from Binance API.
    """

    url = f"{BASE_URL}/api/v3/ticker/price"

    response = requests.get(
        url,
        params={"symbol": symbol},
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    logger.info(f"Fetched price for {symbol}")

    return data
