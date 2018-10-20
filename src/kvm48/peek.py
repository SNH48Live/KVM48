from typing import Iterator, Optional, Tuple

import multiprocessing.pool
import requests


def peek_content_length(url: str) -> Optional[int]:
    try:
        r = requests.head(url, allow_redirects=True, timeout=3)
    except (requests.RequestException, OSError):
        return None
    if r.status_code == 200 and "content-length" in r.headers:
        return int(r.headers["content-length"])
    else:
        return None


def peek_total_size(urls: Iterator[str]) -> Tuple[int, int]:
    with multiprocessing.pool.ThreadPool(processes=16) as pool:
        it = pool.imap_unordered(peek_content_length, urls)
        pool.close()
        pool.join()
        total_size = 0
        unknown_files = 0
        for size in it:
            if size is None:
                unknown_files += 1
            else:
                total_size += size
        return total_size, unknown_files
