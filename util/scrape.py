import argparse
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

logging.basicConfig()
logger = logging.getLogger(__name__)


def refresh_cache(cache_dir: Path, ttl_minutes: float) -> None:
    logger.info("populating/refreshing course catalogue page cache")
    if ttl_minutes == 0:
        logger.info("removing entire cache tree")
        shutil.rmtree(cache_dir)
    pass


def _ttl_expired(file: Path, ttl_minutes: float) -> bool:
    if ttl_minutes == -1:
        return False

    delta_m = (datetime.fromtimestamp(file.stat().st_mtime) - datetime.now()).total_seconds() / 60
    return delta_m > ttl_minutes


def _refresh_cache_item(
    url: str, cache_dir: Path, ttl_minutes: float, *args, **kwargs
) -> bytes:
    """
    We could do this slickly with middleware and requests,
    but this is simpler, and we don't need anything fancy.
    """
    # basic sanitization, this breaks 1:1 mappings between URL:disk cache
    # but for our purposes, this is fine (for example, if 2 URLs differ by a character that's replaced)
    sanitized_path = re.sub(r"[^a-z0-9/]", "_", urlparse(url).path).lstrip("/")
    # we make an assumption here that we'll only be caching HTML
    # if this is violated, it's annoying for manual inspection but won't break anything
    cache_content = (cache_dir / sanitized_path).with_suffix(".cache.html")
    if not cache_content.parent.exists():
        cache_content.parent.mkdir(parents=True, exist_ok=False)
    if not cache_content.exists() or _ttl_expired(cache_content, ttl_minutes):
        resp = requests.get(url).content
        with open(cache_content, "wb") as req_content:
            req_content.write(resp)
    else:
        resp = cache_content.read_bytes()
    return resp


def main():
    # formatter_class shows defaults when script is run with --help
    parser = argparse.ArgumentParser(
        description="scrape", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--cache-ttl",
        type=float,
        default=24 * 60,
        help="Minutes before invalidating cached catalogue pages. "
        "A TTL of 0 will always invalidate the cache, and a TTL of -1 will never invalidate the cache.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Number of maximum workers to use for scraping course pages",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debugging mode.")
    parser.add_argument(
        "--scrape-root",
        type=str,
        default=Path(__file__).parent.parent / "local",
        help="Base directory to store scraper cache and output",
    )
    parser.add_argument(
        "--refresh-cache-only",
        action="store_true",
        help="populates the page cache and makes no further attempt to parse anything",
    )
    args = parser.parse_args()
    debug = args.debug
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.debug("debug mode active")
    logger.debug(f"{args=}")
    root = Path(args.scrape_root).absolute()

    # We prefetch everything we'll need to parse in advance.
    # We do this because it's usually very simple to get all the pages,
    # but a lot harder to get the parsing right.
    # This way, we only need to download once and can try many approaches to parsing
    refresh_cache(root / ".cache", args.cache_ttl)
    if args.refresh_cache_only:
        return
    cache_dir = ().mkdir(exist_ok=True)


if __name__ == "__main__":
    main()
