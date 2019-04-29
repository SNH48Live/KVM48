#!/usr/bin/env python3

import logging
import os
import pathlib
import sys

import peewee
import peewee_migrate

HERE = pathlib.Path(__file__).resolve().parent
MIGRATIONS_DIR = HERE / "migrations"

TEST = os.getenv("TEST")
if TEST:
    db = peewee.SqliteDatabase(":memory:")
else:
    DATA_DIR = HERE / "data"
    DB_PATH = DATA_DIR / "data.db"
    db = peewee.SqliteDatabase(
        str(DB_PATH), pragmas={"foreign_keys": "on", "journal_mode": "wal"}
    )
logger = logging.getLogger(__name__)


class _BaseModel(peewee.Model):
    class Meta:
        database = db


class PerfVOD(_BaseModel):
    # Canonical VOD id
    canon_id = peewee.TextField(primary_key=True)

    # live.48.cn club id
    # - SNH48: 1
    # - BEJ48: 2
    # - GNZ48: 3
    # - SHY48: 4
    # - CKG48: 5
    l4c_club_id = peewee.IntegerField()
    # live.48.cn VOD id (a naturally increasing index number)
    # live.48.cn VOD url takes the form of:
    #    https://live.48.cn/Index/invedio/club/{l4c_club_id}/id/{l4c_id}
    l4c_id = peewee.IntegerField(unique=True)

    title = peewee.TextField()
    subtitle = peewee.TextField(null=True)
    start_time = peewee.IntegerField()

    sd_stream = peewee.TextField(null=True)
    hd_stream = peewee.TextField(null=True)
    # FHD streams are a scam for VODs created after October 2018. See
    # https://github.com/SNH48Live/KVM48/issues/7.
    fhd_stream = peewee.TextField(null=True)

    @property
    def l4c_url(self):
        return (
            f"https://live.48.cn/Index/invedio/club/{self.l4c_club_id}/id/{self.l4c_id}"
        )


def init_database(logger=logger):
    if not TEST:
        DATA_DIR.mkdir(exist_ok=True)
    peewee_migrate.Router(db, migrate_dir=str(MIGRATIONS_DIR), logger=logger).run()
