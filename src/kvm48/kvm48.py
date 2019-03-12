#!/usr/bin/env python3

import argparse
import os
import re
import sys
import tempfile
import time

import arrow

from . import (
    aria2,
    caterpillar,
    config,
    edit,
    koudai,
    lock,
    peek,
    persistence,
    update,
    utils,
)
from .config import DEFAULT_CONFIG_FILE, ConfigError
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

KVM48 also offers a perf mode for downloading performance VODs. See
documentation for details: https://github.com/SNH48Live/KVM48#perf-mode

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

PERF_MODE_INSTRUCTIONS = """\
# Each line contains a VOD ID and the path to download to. You may edit
# the path, but please don't touch the ID. You may ignore a VOD and
# hence drop it from the download queue by adding a pound (#) to the
# beginning of the line, or removing the line entirely. Conversely, if
# there are auto-ignored items (e.g. ones you've previously downloaded),
# you can remove the pound-initiated prefix to re-add it to the download
# queue.
#
# Paths may be auto-filtered (transformed or ignored) with a
# user-supplied script. Please refer to the documentation [1] for
# details; a production-ready example is available at [2].
#
# The instructions text you're reading can be suppressed by setting
# perf.instructions to off in your config file.
#
# [1] https://github.com/SNH48Live/KVM48#perf-mode
# [2] https://github.com/SNH48Live/KVM48/wiki/Perf-mode-filter

"""


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


def dump_environment():
    import platform

    print("Platform:", platform.platform(), file=sys.stderr)
    print("Python version:", platform.python_version(), file=sys.stderr)
    print("Python executable:", sys.executable, file=sys.stderr)
    print("KVM48 version:", __version__, file=sys.stderr)
    sys.stderr.write("\n")


def main():
    try:
        debug = True

        conf = config.Config()
        config_template_dumped = conf.dump_config_template()
        conf.dump_filter_template()

        parser = argparse.ArgumentParser(
            prog="kvm48",
            description=HELP,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        newarg = parser.add_argument
        newarg(
            "-m",
            "--mode",
            choices=["std", "perf"],
            default="std",
            help="operation mode (std or perf): "
            "std is the standard mode for downloading individual members' VODs; "
            "perf is the mode for downloading performance VODs",
        )
        newarg("-p", "--perf", action="store_true", help="short for '--mode perf'")
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
            "-n",
            "--dry",
            action="store_true",
            help="print URL & filename combos but do not download",
        )
        newarg("--config", help="use this config file instead of the default")
        newarg(
            "--filter",
            help="use this filter source file instead of the default "
            "(see perf mode documentation)",
        )
        newarg(
            "--edit",
            action="store_true",
            help="open text editor to edit the config file",
        )
        newarg(
            "-M",
            "--multiple-instances",
            action="store_true",
            help="allow multiple instances of kvm48 to run at the same time "
            "(by default only one instance is allowed to run); "
            "use this option with causion",
        )
        newarg(
            "--dump-config-template",
            action="store_true",
            help="dump latest configuration file template to stdout and exit",
        )
        newarg("--version", action="version", version=__version__)
        newarg("--debug", action="store_true")
        args = parser.parse_args()

        if args.dump_config_template:
            sys.stdout.write(config.CONFIG_TEMPLATE)
            sys.exit(0)

        mode = args.mode
        debug = args.debug

        if args.debug:
            dump_environment()

        if args.perf:
            mode = "perf"

        if args.edit:
            edit.launch_editor(args.config or config.DEFAULT_CONFIG_FILE)
            sys.exit(0)

        if config_template_dumped:
            # Onboarding; do not proceed to config loading stage.
            sys.exit(1)

        conf.mode = mode
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
            update.check_update_or_print_whats_new()

        if not args.multiple_instances:
            lock.lock_to_one_instance()

        if mode == "std":
            if not conf.names:
                raise ConfigError("names not specified")
            sys.stderr.write(
                "Searching for VODs in the date range %s to %s for: %s\n"
                % (from_.date(), to_.date(), ", ".join(conf.names))
            )
            vod_list = list(
                reversed(
                    list(
                        koudai.list_vods(
                            from_,
                            to_.shift(days=1),
                            group_id=conf.group_id,
                            show_progress=True,
                            show_progress_threshold=5,
                        )
                    )
                )
            )
        elif mode == "perf":
            conf.load_filter("perf", args.filter)
            sys.stderr.write(
                "Searching for VODs in the date range %s to %s for %s\n"
                % (from_.date(), to_.date(), conf.group_name)
            )
            vod_list = list(
                reversed(
                    list(
                        koudai.list_perf_vods(
                            from_,
                            to_.shift(days=1),
                            group_id=conf.group_id,
                            show_progress=True,
                            show_progress_threshold=5,
                        )
                    )
                )
            )
            tmpfd, tmpfile = tempfile.mkstemp(suffix=".txt", prefix="kvm48-")
            try:
                existing_ids = set(persistence.get_existing_perf_ids())
            except Exception:
                existing_ids = set()
            with os.fdopen(tmpfd, "w", encoding="utf-8") as fp:
                if conf.perf_instructions:
                    fp.write(PERF_MODE_INSTRUCTIONS)
                for vod in vod_list:
                    vod.filename = "%s %s %s.mp4" % (
                        vod.start_time.strftime("%Y%m%d"),
                        vod.title.strip(),
                        vod.subtitle.strip(),
                    )
                    vod.filepath = conf.filepath(vod)
                    filtered_filepath = conf.filter(vod.filepath)
                    if filtered_filepath is None:
                        print("#x", vod.id, vod.filepath, file=fp)
                    else:
                        vod.filepath = filtered_filepath
                        if vod.id in existing_ids:
                            print("#-", vod.id, vod.filepath, file=fp)
                        else:
                            print(vod.id, vod.filepath, file=fp)
            sys.stderr.write(
                "Launching text editor for '%s'\n" % tmpfile
                + "Program will resume once you save the file and exit the text editor...\n"
            )
            edit.launch_editor(
                tmpfile,
                editor=conf.editor,
                opts=conf.editor_opts,
                blocking=True,
                raise_=True,
            )
            id2vod = {vod.id: vod for vod in vod_list}
            vod_list = []
            seen = set()
            with open(tmpfile, encoding="utf-8") as fp:
                for line in fp:
                    # Strip BOM, which Notepad insists on inserting.
                    line = line.strip().lstrip("\uFEFF")
                    if not line or line.startswith("#"):
                        continue
                    m = re.match(r"^(?P<id>\w+)\s+(?P<path>.*)$", line)
                    if not m:
                        raise ValueError("malformed line: %s" % repr(line))
                    id = m.group("id")
                    if id in seen:
                        raise ValueError("duplicate VOD ID: %s" % id)
                    if id not in id2vod:
                        raise ValueError("VOD ID not found: %s" % id)
                    filepath = m.group("path")
                    if os.path.isabs(filepath):
                        raise ValueError("absolute path not allowed: %s" % filepath)
                    if not filepath.endswith(".mp4"):
                        raise ValueError("extension is not .mp4: %s" % filepath)
                    filepath = utils.sanitize_filepath(filepath)
                    vod = id2vod[id]
                    vod.filepath = filepath
                    vod_list.append(vod)
                    seen.add(id)
            sys.stderr.write("Resolving VOD URLs...\n")
            koudai.resolve_perf_vods(
                vod_list, show_progress=True, show_progress_threshold=5
            )
        else:
            raise ValueError("unrecognized mode %s" % repr(mode))

        targets = []
        a2_targets = []
        m3u8_targets = []
        # *_unfinished_targets store targets that aren't already downloaded.
        a2_unfinished_targets = []
        m3u8_unfinished_targets = []
        existing_filepaths = set()
        for vod in vod_list:
            if (mode == "std" and vod.name in conf.names) or mode == "perf":
                url = vod.vod_url
                src_ext = utils.extension_from_url(vod.vod_url, dot=True)
                base, _ = os.path.splitext(conf.filepath(vod))

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

        if mode == "perf":
            # Alert to non-1080p VODs.
            non_1080p_vod_found = False
            for url in new_urls:
                if "/chaoqing/" in url:
                    continue
                elif "/gaoqing/" in url:
                    quality = "720p"
                elif "/liuchang/" in url:
                    quality = "480p"
                else:
                    continue
                non_1080p_vod_found = True
                sys.stderr.write("[WARNING] %s is %s, not 1080p\n" % (url, quality))
            if non_1080p_vod_found:
                sys.stderr.write(
                    "See <https://github.com/SNH48Live/KVM48/issues/7> for details about this issue.\n"
                )

        # Make subdirectories.
        if not args.dry:
            subdirs = set(
                os.path.dirname(filepath)
                for url, filepath in a2_unfinished_targets + m3u8_unfinished_targets
            )
            for subdir in subdirs:
                os.makedirs(os.path.join(conf.directory, subdir), exist_ok=True)

        # Report download sizes.
        if a2_unfinished_targets:
            total_size, unknown_files = peek.peek_total_size(
                url for url, _ in a2_unfinished_targets
            )
            msg = "{} direct downloads, total size: {:,} bytes".format(
                len(a2_unfinished_targets), total_size
            )
            if unknown_files > 0:
                msg += " (size of %d files could not be determined)" % unknown_files
            msg += "\n"
            sys.stderr.write(msg)
        else:
            sys.stderr.write("No new direct downloads.\n")

        if m3u8_unfinished_targets:
            sys.stderr.write(
                "%d M3U8 VODs to download, total size unknown\n"
                % len(m3u8_unfinished_targets)
            )
        else:
            sys.stderr.write("No new M3U8 downloads.\n")

        if args.dry:
            sys.exit(0)

        exit_status = 0
        downloaded_files = []

        # Write the caterpillar manifest first so that we don't need to
        # wait until aria2 is finished.
        m3u8_manifest = os.path.join(conf.directory, "m3u8.txt")
        if m3u8_unfinished_targets:
            m3u8_unfinished_targets = caterpillar.write_manifest(
                m3u8_unfinished_targets, m3u8_manifest, target_directory=conf.directory
            )

        if a2_unfinished_targets:
            a2_manifest = os.path.join(conf.directory, "aria2.txt")
            a2_dest_files = [
                os.path.join(conf.directory, path) for _, path in a2_unfinished_targets
            ]
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

            for filepath in a2_dest_files:
                if os.path.exists(filepath) and not os.path.exists(filepath + ".aria2"):
                    downloaded_files.append(filepath)

        if m3u8_unfinished_targets:
            requirement_met = caterpillar.check_caterpillar_requirement()
            if not requirement_met:
                sys.stderr.write(
                    "\n[ERROR] caterpillar requirement not met, cannot download M3U8 VODs.\n"
                    "caterpillar batch manifest has been written to '%s'.\n\n"
                    % m3u8_manifest
                )
                exit_status = 1
            else:
                m3u8_dest_files = [
                    os.path.join(conf.directory, path)
                    for _, path in m3u8_unfinished_targets
                ]
                for attempt in range(3):
                    if attempt == 0:
                        sys.stderr.write(
                            "\nProcessing M3U8 downloads with caterpillar...\n\n"
                        )
                    else:
                        sys.stderr.write(
                            "\nRetrying M3U8 downloads with caterpillar...\n\n"
                        )
                    m3u8_unfinished_targets = caterpillar.write_manifest(
                        m3u8_unfinished_targets,
                        m3u8_manifest,
                        target_directory=conf.directory,
                    )
                    caterpillar_exit_status = caterpillar.download(m3u8_manifest)
                    if caterpillar_exit_status == 0:
                        os.unlink(m3u8_manifest)
                        m3u8_unfinished_targets = []
                        break
                else:
                    m3u8_unfinished_targets = caterpillar.write_manifest(
                        m3u8_unfinished_targets,
                        m3u8_manifest,
                        target_directory=conf.directory,
                    )
                    sys.stderr.write(
                        "\n[ERROR] caterpillar failed to download the following VODs:\n\n"
                    )
                    for url, filepath in m3u8_unfinished_targets:
                        sys.stderr.write("\t%s\t%s\n" % (url, filepath))
                    sys.stderr.write(
                        "\ncaterpillar batch manifest have been written to '%s' "
                        "in case you want to retry manually.\n\n" % m3u8_manifest
                    )
                    exit_status = 1

                for filepath in m3u8_dest_files:
                    if os.path.exists(filepath):
                        downloaded_files.append(filepath)

        if mode == "perf":
            persistence.insert_perf_ids([vod.id for vod in vod_list])

        if downloaded_files:
            sys.stderr.write("Downloaded %d files:\n" % len(downloaded_files))
            for filepath in downloaded_files:
                print(os.path.normpath(filepath), file=sys.stderr)

        if exit_status == 0:
            sys.stderr.write("All is well.\n")
        else:
            sys.stderr.write(
                "[SUMMARY] %d direct downloads failed, %d M3U8 downloads failed\n"
                % (len(a2_unfinished_targets), len(m3u8_unfinished_targets))
            )

        sys.exit(exit_status)
    except ConfigError as exc:
        if debug:
            raise
        else:
            sys.stderr.write("Configuration error: %s\n" % exc)
            sys.stderr.write(
                "Please run `kvm48 --edit` to fix your config file.\n"
                "A simple example can be found at <https://github.com/SNH48Live/KVM48#config-sample>, "
                "and the full documentation of all configuration options is right above that.\n"
            )
            sys.exit(1)
    except Exception as exc:
        if debug:
            raise
        else:
            sys.stderr.write("%s: %s\n" % (type(exc).__name__, str(exc)))
            sys.stderr.write(
                "[NOTICE] KVM48 halted due to an exception. If you believe this is a bug, "
                "please read <https://github.com/SNH48Live/KVM48#reporting-bugs> "
                "before reporting the bug, thank you.\n"
            )
            sys.exit(1)
    except KeyboardInterrupt:
        if debug:
            raise
        else:
            print("Interrupted.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
