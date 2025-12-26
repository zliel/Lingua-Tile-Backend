import logging
import sys
from pythonjsonlogger.jsonlogger import JsonFormatter


def setup_logging():
    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(module)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # List of loggers to configure
    loggers = [
        logging.getLogger(),
        logging.getLogger("uvicorn.error"),
    ]

    for logger in loggers:
        for h in logger.handlers[:]:
            logger.removeHandler(h)

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Prevent propagation to avoid duplicate logs if root also picks it up
        logger.propagate = False
