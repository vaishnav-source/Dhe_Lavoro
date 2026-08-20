"""
One-time-use script: resets `description` to NULL for every active job of
a source, so the next detail backfill run re-fetches and re-extracts it
with the current (fixed) html_cleaner.py logic.

Only run this once after a description-extraction fix — running it
repeatedly just makes every backfill run re-hit the source site for no
reason.

Usage:
  python -m scraper.reset_descriptions --source infopark
  python -m scraper.reset_descriptions --source technopark
  python -m scraper.reset_descriptions --source all
"""
import argparse
import sys

from scraper.common.db_writer import reset_descriptions_for_reformat
from scraper.common.logger import get_logger

log = get_logger(__name__)

VALID_SOURCES = ["infopark", "technopark"]


def run_reset(source: str) -> dict:
    sources = VALID_SOURCES if source == "all" else [source]
    results = {}
    for src in sources:
        results[src] = reset_descriptions_for_reformat(src)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=VALID_SOURCES + ["all"], required=True)
    args = parser.parse_args()

    outcome = run_reset(args.source)
    log.info("Reset complete: %s", outcome)
    print(outcome)
    if sum(outcome.values()) == 0:
        sys.exit(0)