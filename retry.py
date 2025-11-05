import functools
import logging
import time
from typing import Any, Callable, Tuple, Type

logger = logging.getLogger(__name__)

def retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    A decorator to retry a function call upon specific exceptions with exponential backoff.

    Args:
        retries (int): The maximum number of attempts. Must be 1 or greater.
        delay (float): The initial delay between retries in seconds. Must be positive.
        backoff (float): The factor by which the delay is multiplied after each retry.
                         Must be 1 or greater.
        exceptions (Tuple[Type[Exception], ...]): A tuple of exception types to catch and retry on.

    Returns:
        Callable: The wrapped function with retry logic.

    Raises:
        ValueError: If `retries`, `delay`, or `backoff` arguments are invalid.
    """
    if retries < 1:
        raise ValueError("retries must be at least 1")
    if delay <= 0:
        raise ValueError("delay must be positive")
    if backoff < 1:
        raise ValueError("backoff must be at least 1")

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(1, retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        break

                    logger.warning(
                        f"Attempt {attempt}/{retries} for '{func.__name__}' failed with "
                        f"{type(e).__name__}: {e}. Retrying in {current_delay:.2f} seconds..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            logger.error(
                f"Function '{func.__name__}' failed after {retries} attempts."
            )
            raise last_exception

        return wrapper
    return decorator
