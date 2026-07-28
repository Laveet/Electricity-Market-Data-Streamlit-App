import logging
import sys
import structlog
from config.settings import settings


def configure_logger() -> structlog.stdlib.BoundLogger:
    """Configures structured JSON logging for production observability."""
    logging_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure standard logging to interface with structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer()
            if not settings.DEBUG
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("energy_data_engine")


# Global logger instance
logger = configure_logger()