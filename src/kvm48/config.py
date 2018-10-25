import os
import re
import sys
from typing import List

import arrow
import attrdict
import yaml

from .dirs import USER_CONFIG_DIR
from .koudai import VOD


if os.path.exists(os.path.expanduser("~/.config/kvm48/config.yml")):
    # Legacy config path is respected.
    DEFAULT_CONFIG_DIR = os.path.normcase(os.path.expanduser("~/.config/kvm48/"))
else:
    DEFAULT_CONFIG_DIR = USER_CONFIG_DIR
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_DIR, "config.yml")
DEFAULT_NAMING_PATTERN = "%(date_c)s %(name)s口袋%(type)s %(title)s.%(ext)s"
CONFIG_TEMPLATE = """\
# ID of group to monitor, if all members you monitor are in a single
# group (this may save you a few API requests each time). Leave as 0 if
# you want to monitor multiple groups.
#
# Group IDs:
# - SNH48: 10;
# - BEJ48: 11;
# - GNZ48: 12;
# - SHY48: 13;
# - CKG48: 14.
group_id: 0

# Names of members to monitor and download.
#
# Example:
# names:
# - 莫寒
# - 张语格
names:

# Default time span (inclusive), in days, to check for VODs.
#
# By default, the last day to check is today, and the default time span
# is 1 day (inclusive), which means only VODs from today are checked. If
# the span is set to 2, then VODs from both yesterday and today are
# checked. So on and so forth.
#
# The date range could be customized on the command line via --from,
# --to, and --span.
span: 1

# Destination directory for downloaded VODs. Tilde expansion is allowed.
# The default is the current working directory.
#
# Example:
# directory: ~/Downloads
directory:

# File naming pattern. The following replacement strings are available:
# - %(date)s: date in the form YYYY-MM-DD, e.g. 2018-02-11;
# - %(date_c)s: compact date in the form YYYYMMDD, e.g., 20180211;
# - %(datetime)s: starting datetime in the form YYYY-MM-DD HH.MM.SS, e.g. 2018-02-11 18.57.32;
# - %(datetime_c)s: compact starting datetime in the form YYYYMMDDHHMMSS, e.g., 20180211185732;
# - %(id)s: server-assigned alphanumeric VOD ID, 5a80219c0cf29aa343fbe009;
# - %(name)s: member name, e.g., 莫寒;
# - %(type)s: type of the VOD, either 直播 or 电台;
# - %(title)s: title of the VOD, e.g. "一人吃火锅的人生成就(๑˙ー˙๑)";
# - %(ext)s: extension of the file (without leading dot), e.g. mp4;
# - %%: a literal percent sign should be escaped like this.
#
# Note that kvm48 handles filename conflicts automatically by appending
# numbers to filenames.
#
# The default pattern is
#   %(date_c)s %(name)s口袋%(type)s %(title)s.%(ext)s
# An example file name produced by this pattern is
#   20180211 莫寒口袋直播 一人吃火锅的人生成就(๑˙ー˙๑).mp4
naming:

# Whether to put VODs in named subdirectories. If turned on, each member
# will have her own subdirectory named after her where all her VODs will
# go. Default is off.
#
# New in v0.3.
# named_subdirs: off

# Whether to allow daily update checks for KVM48. Default is on.
# update_checks: on
"""


class ConfigError(Exception):
    pass


class Config(object):
    def __init__(self):
        self.group_id = 0  # type: int
        self.names = []  # type: List[str]
        self.span = 1  # type: int
        self.directory = None  # type: str
        self.naming = DEFAULT_NAMING_PATTERN  # type: str
        self.named_subdirs = False  # type: bool

    def filename(self, vod: VOD) -> str:
        unsanitized = self.naming % {
            "date": vod.start_time.strftime("%Y-%m-%d"),
            "date_c": vod.start_time.strftime("%Y%m%d"),
            "datetime": vod.start_time.strftime("%Y-%m-%d %H.%M.%S"),
            "datetime_c": vod.start_time.strftime("%Y%m%d%H%M%S"),
            "id": vod.id,
            "name": vod.name,
            "type": vod.type,
            "title": vod.title.strip(),
            "ext": os.path.splitext(vod.vod_url)[1][1:],
        }
        # Strip control characters (0x00-0x1F, 0x7F), and use homoglyphs
        # (Halfwidth and Fullwidth Forms block, U+FF00 - U+FFEF) for
        # characters illegal in exFAT/NTFS:
        #
        # " => U+FF02 FULLWIDTH QUOTATION MARK (＂)
        # * => U+FF0A FULLWIDTH ASTERISK (＊)
        # / => U+FF0F FULLWIDTH SOLIDUS (／)
        # : => U+FF1A FULLWIDTH COLON (：)
        # < => U+FF1C FULLWIDTH LESS-THAN SIGN (＜)
        # > => U+FF1E FULLWIDTH GREATER-THAN SIGN (＞)
        # ? => U+FF1F FULLWIDTH QUESTION MARK (？)
        # \ => U+FF3C FULLWIDTH REVERSE SOLIDUS (＼)
        # | => U+FF5C FULLWIDTH VERTICAL LINE (｜)
        #
        # Also replace whitespace characters with the space
        return re.sub(r"[\x00-\x1f\x7f]+", "", unsanitized).translate(
            str.maketrans(
                '"*/:<>?\\|\t\n\r\f\v',
                "\uFF02\uFF0A\uFF0F\uFF1A\uFF1C\uFF1E\uFF1F\uFF3C\uFF5C     ",
            )
        )

    def filepath(self, vod: VOD) -> str:
        if self.named_subdirs:
            return vod.name + os.sep + self.filename(vod)
        else:
            return self.filename(vod)

    def load(self, config_file: str = None) -> None:
        if not config_file:
            config_file = DEFAULT_CONFIG_FILE
        try:
            with open(config_file, encoding="utf-8") as fp:
                obj = yaml.load(fp.read())
        except Exception as exc:
            raise ConfigError("failed to load/parse %s: %s" % (config_file, str(exc)))

        try:
            self.group_id = int(obj.get("group_id") or 0)
        except ValueError:
            raise ConfigError("invalid group_id; must be an integer")
        if self.group_id not in (0, 10, 11, 12, 13, 14):
            raise ConfigError(
                "unrecognized group_id; must be one of 0, 10, 11, 12, 13, and 14"
            )

        self.names = obj["names"]
        if not isinstance(self.names, list) or not all(
            isinstance(v, str) for v in self.names
        ):
            raise ConfigError("invalid names; names must be a nonempty list of strings")

        try:
            self.span = max(int(obj.get("span") or 1), 1)
        except ValueError:
            raise ConfigError("invalid span; must be an integer")

        directory = obj.get("directory")
        if directory:
            directory = os.path.abspath(os.path.expanduser(directory))
            if not os.path.isdir(directory):
                raise ConfigError("nonexistent directory: %s" % directory)
            self.directory = directory
        else:
            self.directory = os.getcwd()

        self.naming = obj.get("naming") or DEFAULT_NAMING_PATTERN
        self.test_naming_pattern()

        self.named_subdirs = obj.get("named_subdirs", False)
        if not isinstance(self.named_subdirs, bool):
            raise ConfigError("invalid named_subdirs; named_subdirs must be a boolean")

        self.update_checks = obj.get("update_checks", True)
        if not isinstance(self.update_checks, bool):
            raise ConfigError("invalid update_checks; update_checks must be a boolean")

    def test_naming_pattern(self) -> None:
        try:
            self.filename(
                VOD(
                    {
                        "id": "5a80219c0cf29aa343fbe009",
                        "member_id": 35,
                        "room_id": 3872010,
                        "type": "直播",
                        "name": "莫寒",
                        "title": "一人吃火锅的人生成就(๑˙ー˙๑)",
                        "start_time": arrow.get("2018-02-11T18:57:32.164000+08:00"),
                        "vod_url": "https://mp4.48.cn/live/82b50b91-28f8-4182-8ac0-3ca4d0202636.mp4",
                        "danmaku_url": "https://source.48.cn/mediasource/live/lrc/5a80219c0cf29aa343fbe009.lrc",
                    }
                )
            )
        except Exception:
            raise ConfigError("bad naming pattern: %s" % self.naming)

    @staticmethod
    def dump_config_template():
        if not os.path.isdir(DEFAULT_CONFIG_DIR):
            os.makedirs(DEFAULT_CONFIG_DIR, mode=0o700)
        if (
            os.path.isfile(DEFAULT_CONFIG_FILE)
            and os.stat(DEFAULT_CONFIG_FILE).st_size > 0
        ):
            return
        with open(DEFAULT_CONFIG_FILE, "w", encoding="utf-8") as fp:
            fp.write(CONFIG_TEMPLATE)
        print(
            ("Configuration template written to %s.\n" % DEFAULT_CONFIG_FILE)
            + "Please edit the file to suit your needs before using kvm48.\n",
            file=sys.stderr,
        )
