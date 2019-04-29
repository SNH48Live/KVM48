def migrate(migrator, database, fake=False, **kwargs):
    if not fake:
        database.cursor().executescript(
            """\
CREATE TABLE "perfvod" (
    "canon_id" TEXT NOT NULL PRIMARY KEY,
    "l4c_club_id" INTEGER NOT NULL,
    "l4c_id" INTEGER NOT NULL, "title" TEXT NOT NULL,
    "subtitle" TEXT,
    "start_time" INTEGER NOT NULL,
    "sd_stream" TEXT,
    "hd_stream" TEXT,
    "fhd_stream" TEXT
);
CREATE UNIQUE INDEX "perfvod_l4c_id" ON "perfvod" ("l4c_id");"""
        )


def rollback(migrator, database, fake=False, **kwargs):
    if not fake:
        migrator.sql("DROP TABLE perfvod;")
