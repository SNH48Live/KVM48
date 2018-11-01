import functools
import os
import sqlite3
from typing import Iterable, List

from .dirs import USER_DATA_DIR


perf_id_conn = None


def ensure_perf_id_database(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        global perf_id_conn
        if not perf_id_conn:
            if not os.path.exists(USER_DATA_DIR):
                os.makedirs(USER_DATA_DIR, exist_ok=True)
            perf_id_conn = sqlite3.connect(os.path.join(USER_DATA_DIR, "perf_id.db"))
            with perf_id_conn:
                perf_id_conn.execute(
                    "CREATE TABLE IF NOT EXISTS id (id TEXT NOT NULL PRIMARY KEY)"
                )
        return f(*args, **kwargs)

    return wrapper


@ensure_perf_id_database
def get_existing_perf_ids() -> List[str]:
    with perf_id_conn:
        return [id for id, in perf_id_conn.execute("SELECT id FROM id").fetchall()]


@ensure_perf_id_database
def insert_perf_ids(ids: Iterable[str]) -> None:
    with perf_id_conn:
        perf_id_conn.executemany("INSERT OR IGNORE INTO id(id) VALUES (?)", [(id,) for id in ids])
