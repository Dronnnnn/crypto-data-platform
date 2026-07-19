import time

from crypto_data_platform.common.logger import get_logger

logger = get_logger(__name__)


def sleep_before_retry(attempt: int) -> None:
    """
    Sleep before next retry using exponential backoff.

    1 -> 2 seconds
    2 -> 4 seconds
    3 -> 8 seconds
    """

    delay = 2**attempt

    logger.info(
        "Retrying in %s seconds...",
        delay,
    )

    time.sleep(delay)
