import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging(level: str) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    root_logger.handlers = [handler]
