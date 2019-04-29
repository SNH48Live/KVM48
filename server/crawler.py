#!/usr/bin/env python3

import argparse
import datetime
import functools
import gzip
import logging
import multiprocessing.pool
import pathlib
import re
import threading
import time
import urllib.parse

import bs4
import peewee
import requests

from database import PerfVOD, init_database


HERE = pathlib.Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
HTML_ARCHIVE_DIR = DATA_DIR / "html"
LOG_DIR = HERE / "logs"
FMT = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"
)

HTML_ARCHIVE_DIR.mkdir(exist_ok=True, parents=True)
LOG_DIR.mkdir(exist_ok=True)


def init_logger():
    logger = logging.getLogger("crawler")
    logger.setLevel(logging.DEBUG)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(FMT)
    logger.addHandler(sh)

    fh = logging.FileHandler(LOG_DIR.joinpath("crawler.log"), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(FMT)
    logger.addHandler(fh)

    return logger


logger = init_logger()


def retrieve_seen_urls():
    return set(
        f"https://live.48.cn/Index/invedio/club/{v.l4c_club_id}/id/{v.l4c_id}"
        for v in PerfVOD.select().order_by(PerfVOD.l4c_id.desc())
    )


init_database(logger=logger)
seen_urls = retrieve_seen_urls()
seen_urls_lock = threading.Lock()


class UnretriableException(Exception):
    pass


# - 'what' is a string describing what the function does, used in
#   logging. The string is treated as a format template that takes all
#   of the function's arguments (args and kwargs).
# - 'tries' is the number of tries allowed.
# - 'catch_all' determines whether all exceptions are caught or just
#   RuntimeErrors are caught (thus allowing callers to only trap known
#   exceptions). Even when 'catch_all' is True, one can still raise an
#   UnretriableException to break out immediately.
def retry(what="", tries=3, catch_all=False):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            what_ = what.format(*args, **kwargs)
            ExpectedException = Exception if catch_all else RuntimeError
            for ntry in range(1, tries + 1):
                try:
                    return f(*args, **kwargs)
                except ExpectedException as e:
                    if isinstance(e, UnretriableException):
                        raise
                    if ntry == tries:
                        logger.error(f"{what_}: {e} (failed after {tries} tries)")
                        raise
                    else:
                        logger.warning(f"{what_}: {e}")
                        logger.info(f"{what_}: retrying in {2 ** ntry}s")
                        time.sleep(2 ** ntry)

        return wrapper

    return decorator


@retry("GET {0}")
def request_page(url):
    logger.info(f"GET {url}")
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        return r.text
    except (requests.RequestException, OSError):
        raise RuntimeError("network timeout/error")


@retry("{0}", catch_all=True)
def fetch_vod(url):
    if url in seen_urls:
        return

    m = re.match(r"^https://live.48.cn/Index/invedio/club/(\d+)/id/(\d+)$", url)
    if not m:
        raise ValueError(f"malformed VOD URL: {url}")
    l4c_club_id = int(m.group(1))
    l4c_id = int(m.group(2))

    html = request_page(url)
    html_save_dir = HTML_ARCHIVE_DIR / f"{l4c_club_id}"
    html_save_dir.mkdir(exist_ok=True)
    html_save_dest = html_save_dir / f"{l4c_id}.html.gz"
    with gzip.open(html_save_dest, "wt") as fp:
        fp.write(html)
    soup = bs4.BeautifulSoup(html, "html.parser")
    canon_id = soup.select_one("#vedio_id")["value"]
    title = soup.select_one(".title1").text.strip()
    subtitle = soup.select_one(".title2").text.strip()
    m = re.match(r"^(.*)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})$", subtitle)
    assert m
    subtitle = m.group(1).strip()
    start_time = datetime.datetime.strptime(
        f"{m.group(2)} +0800", "%Y-%m-%d %H:%M:%S %z"
    ).timestamp()
    sd_stream_tag = soup.select_one("#liuchang_url")
    sd_stream = sd_stream_tag["value"] if sd_stream_tag else None
    hd_stream_tag = soup.select_one("#gao_url")
    hd_stream = hd_stream_tag["value"] if hd_stream_tag else None
    fhd_stream_tag = soup.select_one("#chao_url")
    fhd_stream = fhd_stream_tag["value"] if fhd_stream_tag else None
    if not (sd_stream or hd_stream or fhd_stream):
        raise RuntimeError(f"{url}: no stream found")

    try:
        PerfVOD.create(
            canon_id=canon_id,
            l4c_club_id=l4c_club_id,
            l4c_id=l4c_id,
            title=title,
            subtitle=subtitle,
            start_time=start_time,
            sd_stream=sd_stream,
            hd_stream=hd_stream,
            fhd_stream=fhd_stream,
        )
    except peewee.IntegrityError as e:
        # There are duplicate entries on live.48.cn, e.g.,
        # - https://live.48.cn/Index/invedio/club/1/id/2580
        # - https://live.48.cn/Index/invedio/club/1/id/2592
        # We need to let these duplicates through.
        #
        # And there's an actual collision we need to ignore:
        # - https://live.48.cn/Index/invedio/club/3/id/1750
        # - https://live.48.cn/Index/invedio/club/3/id/2451
        # Both have id 5bd81e5a0cf27e320898288b (which looks like a
        # MongoDB ObjectID). How they managed to create the collision,
        # I can't even imagine.
        if canon_id == "5bd81e5a0cf27e320898288b":
            # Known collision, can't do anything about it.
            pass
        else:
            try:
                existing = PerfVOD.get(canon_id=canon_id)
                if existing.start_time != start_time:
                    raise UnretriableException(
                        f"{url}: conflict with {existing.l4c_url}"
                    )
            except peewee.DoesNotExist:
                raise e
    with seen_urls_lock:
        seen_urls.add(url)


def crawl_page(club_id, page, should_not_be_empty=False):
    page_url = f"https://live.48.cn/Index/main/club/{club_id}/p/{page}.html"
    page_html = request_page(page_url)
    soup = bs4.BeautifulSoup(page_html, "html.parser")
    urls = set(
        urllib.parse.urljoin(page_url, a["href"])
        for a in soup.select(".videolist .videos a")
    )
    if not urls and should_not_be_empty:
        # Parser probably broken.
        raise RuntimeError("{page_url}: cannot find VOD links")
    seen_urls_on_page = sorted(urls & seen_urls)
    new_urls_on_page = sorted(urls - seen_urls)
    with multiprocessing.pool.ThreadPool(2) as pool:
        pool.map(fetch_vod, new_urls_on_page)
    m = re.search(r"共(\d+)页", soup.select_one(".p-skip").text)
    total_pages = int(m.group(1))
    return seen_urls_on_page, new_urls_on_page, total_pages


# If full is True, crawl all pages instead of stopping at last seen.
def crawl_club(club_id, limit_pages=None, full=False):
    page = 1
    while True:
        seen_urls_on_page, new_urls_on_page, total_pages = crawl_page(
            club_id, page, should_not_be_empty=page == 1
        )
        if not full and seen_urls_on_page:
            break
        page += 1
        if page > total_pages or (limit_pages and page > limit_pages):
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--full",
        action="store_true",
        help="crawl all pages instead of stopping at last seen",
    )
    parser.add_argument(
        "-L",
        "--limit-pages",
        type=int,
        metavar="N",
        help="only crawl at most the first N pages of each club",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="also crawl VODs of now defunct SHY48 and CKG48",
    )
    args = parser.parse_args()

    club_ids = (1, 2, 3, 4, 5) if args.legacy else (1, 2, 3)
    for club_id in club_ids:
        crawl_club(club_id, limit_pages=args.limit_pages, full=args.full)


if __name__ == "__main__":
    main()
