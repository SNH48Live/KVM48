#!/usr/bin/env python3

import argparse
import os
import re
import sys
import time

import arrow

from . import aria2, caterpillar, config, koudai, peek, update
from .config import DEFAULT_CONFIG_FILE
from .version import __version__


HELP = (
    """\
KVM48, the Koudai48 VOD Manager.

KVM48 downloads all streaming VODs of monitored members in a specified
date range. Monitored members and other options are configured through
the YAML configuration file

  %s

or through a different configuration file specified with the --config
option.

The date range is determined as follows. All date and time are processed
in China Standard Time (UTC+08:00). --from and --to are specified in the
YYYY-MM-DD or MM-DD format.

- If both --from and --to are specified, use those;

- If --to is specified and --from is not, determine the date span
  through --span and the `span' config option (the former takes
  priority), then let the date range be `span' number of days
  (inclusive) ending in the --to date.

  For instance, if --to is 2018-02-18 and span is 7, then the date range
  is 2018-02-12 to 2018-02-18.

- If --from is specified and --to is not, then

  - If --span is explicitly specified on the command line, let the date
    range be `span' number of days starting from the --from date.

  - Otherwise, let the date range be the --from date to today (in
    UTC+08:00).

- If neither --from nor --to is specified, use today (in UTC+08:00) as
  the to date, and determine span in the same way as above.

KVM48 uses aria2 for direct downloads. Certain aria2c options, e.g.,
--max-connection-per-server=16, are enforced within kvm48; most options
should be configured directly in the aria2 config file.

KVM48 optionally uses caterpillar[1] as the M3U8/HLS downloader.
caterpillar is built on top of FFmpeg, the Swiss army knife of
multimedia processing, but it is specifically engineered to not produce
scrambled files when there are timestamp discontinuities or
irregularities in the source, which is all too common with Koudai48's
livestreaming infrastructure. If M3U8 streams are detected and
caterpillar is either not found or does not meet the minimum version
requirement, the URLs and supposed paths are written to disk for
postprocessing at the user's discretion.

[1] https://github.com/zmwangx/caterpillar
"""
    % DEFAULT_CONFIG_FILE
)


def parse_date(s: str) -> arrow.Arrow:
    def date(year: int, month: int, day: int) -> arrow.Arrow:
        return arrow.get(year, month, day, tzinfo="Asia/Shanghai")

    m = re.match(r"^((?P<year>\d{4})-)?(?P<month>\d{2})-(?P<day>\d{2})$", s)
    if not m:
        raise argparse.ArgumentTypeError(
            "%s is not a valid date; " "please use YYYY-MM-DD or MM-DD format" % s
        )

    year = int(m.group("year") or 0)
    month = int(m.group("month"))
    day = int(m.group("day"))

    if year:
        return date(year, month, day)
    else:
        now = arrow.now("Asia/Shanghai")
        dt = date(now.year, month, day)
        if dt <= now:
            return dt
        else:
            return date(now.year - 1, month, day)


def main():
    try:
        debug = True

        conf = config.Config()
        conf.dump_config_template()

        parser = argparse.ArgumentParser(
            prog="kvm48",
            description=HELP,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        newarg = parser.add_argument
        newarg(
            "-f",
            "--from",
            dest="from_",
            type=parse_date,
            metavar="FROM",
            help="starting day of date range",
        )
        newarg(
            "-t",
            "--to",
            dest="to_",
            type=parse_date,
            metavar="TO",
            help="ending day of date range",
        )
        newarg("-s", "--span", type=int, help="number of days in date range")
        newarg(
            "--dry",
            action="store_true",
            help="print URL & filename combos but do not download",
        )
        newarg("--config", help="use this config file instead of the default")
        newarg("--version", action="version", version=__version__)
        newarg("--debug", action="store_true")
        args = parser.parse_args()

        debug = args.debug

        conf.load(args.config)

        if args.span is not None and args.span <= 0:
            raise ValueError("span should be positive")
        span = args.span or conf.span
        today = arrow.get(arrow.now("Asia/Shanghai").date(), "Asia/Shanghai")
        if args.from_ and args.to_:
            from_ = args.from_
            to_ = args.to_
        elif args.to_:
            to_ = args.to_
            from_ = to_.shift(days=-(span - 1))
        elif args.from_:
            from_ = args.from_
            if args.span:
                to_ = from_.shift(days=(args.span - 1))
            else:
                to_ = today
        else:
            to_ = today
            from_ = to_.shift(days=-(span - 1))
        if from_ > to_:
            raise ValueError(
                "from date %s is later than to date %s" % (from_.date(), to_.date())
            )

        if conf.update_checks:
            update.check_update()

        print(
            "Searching for VODs in the date range %s to %s for: %s"
            % (from_.date(), to_.date(), ", ".join(conf.names)),
            file=sys.stderr,
        )

        vod_list = koudai.list_vods(
            from_,
            to_.shift(days=1),
            group_id=conf.group_id,
            show_progress=True,
            show_progress_threshold=5,
        )

        targets = []
        a2_targets = []
        m3u8_targets = []
        # *_unfinished_targets store targets that aren't already downloaded.
        a2_unfinished_targets = []
        m3u8_unfinished_targets = []
        existing_filepaths = set()
        for vod in reversed(list(vod_list)):
            if vod.name in conf.names:
                url = vod.vod_url
                base, src_ext = os.path.splitext(conf.filepath(vod))

                # If source extension is .m3u8, use .mp4 as output
                # extension; otherwise, use the source extension as the
                # output extension.
                ext = ".mp4" if src_ext == ".m3u8" else src_ext

                # Filename deduplication
                filepath = base + ext
                number = 0
                while filepath in existing_filepaths:
                    number += 1
                    filepath = "%s (%d)%s" % (base, number, ext)
                existing_filepaths.add(filepath)

                fullpath = os.path.join(conf.directory, filepath)

                entry = (url, filepath)
                targets.append(entry)
                if src_ext == ".m3u8":
                    m3u8_targets.append(entry)
                    if not os.path.exists(fullpath):
                        m3u8_unfinished_targets.append(entry)
                else:
                    a2_targets.append(entry)
                    if not os.path.exists(fullpath) or os.path.exists(
                        fullpath + ".aria2"
                    ):
                        a2_unfinished_targets.append(entry)

        new_urls = set(
            url for url, _ in a2_unfinished_targets + m3u8_unfinished_targets
        )
        for url, filepath in targets:
            if url in new_urls:
                print("%s\t%s\t*" % (url, filepath))
            else:
                print("%s\t%s" % (url, filepath))

        if not args.dry and conf.named_subdirs:
            subdirs = set(
                os.path.dirname(filepath)
                for url, filepath in a2_unfinished_targets + m3u8_unfinished_targets
            )
            for subdir in subdirs:
                try:
                    os.mkdir(os.path.join(conf.directory, subdir))
                except FileExistsError:
                    pass

        # Only write manifest for new targets
        if not args.dry and m3u8_unfinished_targets:
            m3u8_list = os.path.join(conf.directory, "m3u8.txt")
            with open(m3u8_list, "w", encoding="utf-8") as fp:
                for url, filepath in m3u8_unfinished_targets:
                    print("%s\t%s" % (url, filepath), file=fp)
            print('Info of M3U8 VODs written to "%s"' % m3u8_list, file=sys.stderr)

        if a2_unfinished_targets:
            total_size, unknown_files = peek.peek_total_size(
                url for url, _ in a2_unfinished_targets
            )
            msg = "{} direct downloads, total size: {:,} bytes".format(
                len(a2_unfinished_targets), total_size
            )
            if unknown_files > 0:
                msg += " (size of %d files could not be determined)" % unknown_files
        else:
            msg = "No direct downloads."
        print(msg, file=sys.stderr)

        if m3u8_unfinished_targets:
            print(
                "%d M3U8 VODs to download, total size unknown"
                % len(m3u8_unfinished_targets),
                file=sys.stderr,
            )

        sys.stderr.write("\n")

        exit_status = 0

        download_direct = bool(a2_unfinished_targets)
        download_m3u8_vods = False
        if not args.dry and m3u8_unfinished_targets:
            met = caterpillar.check_caterpillar_requirement()
            if not met:
                # Print message, and sleep for a while so that user may
                # see the message.
                print(
                    "[ERROR] caterpillar requirement not met, cannot download M3U8 VODs. "
                    "Program will resume in 5 seconds...",
                    file=sys.stderr,
                )
                time.sleep(5)
                exit_status = 1
            else:
                download_m3u8_vods = True

        if not args.dry and a2_unfinished_targets:
            a2_manifest = os.path.join(conf.directory, "aria2.txt")
            for attempt in range(3):
                if attempt == 0:
                    sys.stderr.write("\nProcessing direct downloads with aria2...\n\n")
                else:
                    sys.stderr.write("\nRetrying direct downloads with aria2...\n\n")
                a2_unfinished_targets = aria2.write_manifest(
                    a2_unfinished_targets, a2_manifest, target_directory=conf.directory
                )
                a2_exit_status = aria2.download(a2_manifest)
                if a2_exit_status == 0:
                    os.unlink(a2_manifest)
                    a2_unfinished_targets = []
                    break
            else:
                a2_unfinished_targets = aria2.write_manifest(
                    a2_unfinished_targets, a2_manifest, target_directory=conf.directory
                )
                # TODO: error summary at the very end.
                sys.stderr.write(
                    "\n[ERROR] aria2 failed to download the following VODs:\n\n"
                )
                for url, filepath in a2_unfinished_targets:
                    sys.stderr.write("\t%s\t%s\n" % (url, filepath))
                sys.stderr.write(
                    "\naria2 batch input file have been written to '%s' "
                    "in case you want to retry manually.\n\n" % a2_manifest
                )
                exit_status = 1
                time.sleep(5)

        if not args.dry and m3u8_unfinished_targets and download_m3u8_vods:
            # Likewise.
            print("\nProcessing M3U8 VOD downloads...", file=sys.stderr)
            execvp = not download_direct
            exit_status |= caterpillar.download(m3u8_list, execvp=execvp)

        sys.exit(exit_status)
    except Exception as exc:
        if debug:
            raise
        else:
            sys.exit("%s: %s" % (type(exc).__name__, str(exc)))
    except KeyboardInterrupt:
        if debug:
            raise
        else:
            print("Interrupted.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
