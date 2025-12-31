import logging
import sys
from pythonjsonlogger.jsonlogger import JsonFormatter


from app.context import get_request_id


class ContextFilter(logging.Filter):
    """
    Filter that injects the request_id context variable into the log record.
    """

    def filter(self, record):
        record.request_id = get_request_id()
        return True


def setup_logging():
    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    context_filter = ContextFilter()
    handler.addFilter(context_filter)

    # List of loggers to configure
    loggers = [
        logging.getLogger(),
        logging.getLogger("uvicorn.error"),
        logging.getLogger("uvicorn.access"),
    ]

    for logger in loggers:
        for h in logger.handlers[:]:
            logger.removeHandler(h)

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Prevent propagation to avoid duplicate logs if root also picks it up
        logger.propagate = False
