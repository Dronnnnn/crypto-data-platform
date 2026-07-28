from argparse import ArgumentParser

from crypto_data_platform.common.constants import BINANCE_SOURCE
from crypto_data_platform.common.logger import get_logger
from crypto_data_platform.ingestion.api_client import fetch_price
from crypto_data_platform.ingestion.raw_storage import upload_raw_json

logger = get_logger(__name__)


def run_pipeline(symbol: str) -> None:
    logger.info("Starting ingestion pipeline")

    payload = fetch_price(symbol)
    key = upload_raw_json(payload, source=BINANCE_SOURCE, symbol=symbol)

    logger.info("Pipeline finished successfully: s3_key=%s", key)


def main() -> None:
    parser = ArgumentParser()

    parser.add_argument(
        "--symbol",
        default="BTCUSDT",
    )

    args = parser.parse_args()

    run_pipeline(args.symbol)


if __name__ == "__main__":
    main()
