from typing import Iterator, Optional

import multiprocessing.pool
import requests


def peek_content_length(url: str) -> Optional[int]:
    r = requests.head(url, allow_redirects=True, timeout=3)
    if r.status_code == 200 and 'content-length' in r.headers:
        return int(r.headers['content-length'])
    else:
        return None


def peek_total_size(urls: Iterator[str]) -> Optional[int]:
    with multiprocessing.pool.ThreadPool(processes=16) as pool:
        it = pool.imap_unordered(peek_content_length, urls)
        pool.close()
        pool.join()
        sizes = list(it)
        if None in sizes:
            return None
        else:
            return sum(sizes)
