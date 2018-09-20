#!/usr/bin/env python3

import argparse
import os
import re
import sys

import arrow

from . import aria2, config, koudai
from .config import DEFAULT_CONFIG_FILE
from .version import __version__


HELP = '''\
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

KVM48 uses aria2 as the downloader. Certain aria2c options, e.g.,
--max-connection-per-server=16, are enforced within kvm48; most options
should be configured directly in the aria2 config file.
''' % DEFAULT_CONFIG_FILE


def parse_date(s: str) -> arrow.Arrow:
    def date(year: int, month: int, day: int) -> arrow.Arrow:
        return arrow.get(year, month, day, tzinfo='Asia/Shanghai')

    m = re.match(r'^((?P<year>\d{4})-)?(?P<month>\d{2})-(?P<day>\d{2})$', s)
    if not m:
        raise argparse.ArgumentTypeError('%s is not a valid date; '
                                         'please use YYYY-MM-DD or MM-DD format' % s)

    year = int(m.group('year') or 0)
    month = int(m.group('month'))
    day = int(m.group('day'))

    if year:
        return date(year, month, day)
    else:
        now = arrow.now('Asia/Shanghai')
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

        parser = argparse.ArgumentParser(prog='kvm48', description=HELP,
                                         formatter_class=argparse.RawDescriptionHelpFormatter)
        newarg = parser.add_argument
        newarg('-f', '--from', dest='from_', type=parse_date, metavar='FROM',
               help='starting day of date range')
        newarg('-t', '--to', dest='to_', type=parse_date, metavar='TO',
               help='ending day of date range')
        newarg('-s', '--span', type=int, help='number of days in date range')
        newarg('--dry', action='store_true', help='print URL & filename combos but do not download')
        newarg('--config', help='use this config file instead of the default')
        newarg('--version', action='version', version=__version__)
        newarg('--debug', action='store_true')
        args = parser.parse_args()

        debug = args.debug

        conf.load(args.config)

        if args.span is not None and args.span <= 0:
            raise ValueError('span should be positive')
        span = args.span or conf.span
        today = arrow.get(arrow.now('Asia/Shanghai').date(), 'Asia/Shanghai')
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
            raise ValueError('from date %s is later than to date %s' % (from_.date(), to_.date()))

        print('Searching for VODs in the date range %s to %s for: %s' %
              (from_.date(), to_.date(), ', '.join(conf.names)), file=sys.stderr)

        vod_list = koudai.list_vods(from_, to_.shift(days=1), group_id=conf.group_id)

        targets = []
        a2_targets = []
        m3u8_targets = []
        existing_filenames = set()
        for vod in reversed(list(vod_list)):
            if vod.name in conf.names:
                url = vod.vod_url
                base, src_ext = os.path.splitext(conf.filename(vod))

                # If source extension is .m3u8, use .mp4 as output
                # extension; otherwise, use the source extension as the
                # output extension.
                ext = '.mp4' if src_ext == '.m3u8' else src_ext

                # Filename deduplication
                filename = base + ext
                number = 0
                while filename in existing_filenames:
                    number += 1
                    filename = '%s (%d)%s' % (base, number, ext)
                existing_filenames.add(filename)

                entry = (url, filename)
                targets.append(entry)
                if src_ext == '.m3u8':
                    m3u8_targets.append(entry)
                else:
                    a2_targets.append(entry)

        for url, filename in targets:
            print('%s\t%s' % (url, filename))

        if not args.dry and m3u8_targets:
            m3u8_list = os.path.join(conf.directory, 'm3u8.txt')
            with open(m3u8_list, 'w', encoding='utf-8') as fp:
                for url, filename in m3u8_targets:
                    print('%s\t%s' % (url, filename), file=fp)
            print('Info of M3U8 VODs written to "%s" (could be consumed by caterpillar)' % m3u8_list,
                  file=sys.stderr)

        if not args.dry and a2_targets:
            aria2.download(a2_targets, directory=conf.directory)
    except Exception as exc:
        if debug:
            raise
        else:
            sys.exit('%s: %s' % (type(exc).__name__, str(exc)))


if __name__ == '__main__':
    main()
