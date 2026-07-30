import random
import time

from scraper.common.config import MIN_DELAY_SECONDS, MAX_DELAY_SECONDS


def polite_delay() -> None:
    """Sleep a randomized interval so we never hammer the source site
    with fixed-interval requests (also makes traffic look less bot-like)."""
    time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
