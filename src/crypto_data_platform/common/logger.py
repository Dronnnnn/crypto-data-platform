import logging

from crypto_data_platform.common.config import settings


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()

        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(settings.log_level)

    return logger
