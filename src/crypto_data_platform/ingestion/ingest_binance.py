from argparse import ArgumentParser

from crypto_data_platform.common.constants import BINANCE_SOURCE
from crypto_data_platform.common.logger import get_logger
from crypto_data_platform.ingestion.api_client import fetch_symbol_price
from crypto_data_platform.ingestion.storage import save_json
from crypto_data_platform.ingestion.uploader import upload_file

logger = get_logger(__name__)


def run_pipeline(symbol: str) -> None:
    logger.info("Starting ingestion pipeline")

    price = fetch_symbol_price(symbol)

    file_path = save_json(
        price,
        BINANCE_SOURCE,
    )

    upload_file(
        file_path=file_path
    )

    logger.info("Pipeline finished successfully")


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