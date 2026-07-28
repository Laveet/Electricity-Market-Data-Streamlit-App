import asyncio
from functools import wraps
from typing import Callable, Any, Type, Tuple
from src.energy_data_engine.utils.logger import logger


def async_retry(
    retries: int = 3,
    backoff_factor: float = 1.5,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator to retry asynchronous functions with exponential backoff.

    Args:
        retries (int): Maximum number of retries.
        backoff_factor (float): Multiplicative factor for delay calculation.
        exceptions (Tuple[Type[Exception], ...]): Exception types to catch and retry.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            delay = 1.0

            while attempt < retries:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= retries:
                        logger.error(
                            "Async function execution failed after max retries",
                            function=func.__name__,
                            attempts=attempt,
                            error=str(e),
                        )
                        raise e

                    logger.warning(
                        "Execution failed, retrying with exponential backoff...",
                        function=func.__name__,
                        attempt=attempt,
                        next_retry_delay=delay,
                        error=str(e),
                    )

                    await asyncio.sleep(delay)
                    delay *= backoff_factor

        return wrapper

    return decorator