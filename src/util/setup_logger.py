import logging


def setup_logger(log_level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Use AWS handler in lambda and stream handler locally
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        handler.setFormatter(
            fmt=logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

    logger.debug("Logger set up!")
    return logger
