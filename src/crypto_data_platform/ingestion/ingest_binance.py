import argparse

from crypto_data_platform.common.logger import get_logger
from crypto_data_platform.ingestion.api_client import fetch_symbol_price
from crypto_data_platform.ingestion.storage import save_json
from crypto_data_platform.ingestion.uploader import upload_file

logger = get_logger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download market data from Binance."
    )

    parser.add_argument(
        "--symbol",
        required=True,
        help="Trading pair, for example BTCUSDT",
    )

    return parser.parse_args()


def run_pipeline(symbol: str) -> None:
    logger.info("Starting ingestion pipeline")

    data = fetch_symbol_price(symbol)

    file_path = save_json(data)

    upload_file(file_path, 'raw')

    logger.info("Pipeline finished successfully")


def main():
    args = parse_args()
    run_pipeline(args.symbol)


if __name__ == "__main__":
    main()