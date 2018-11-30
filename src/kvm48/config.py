import importlib
import os
import sys
from typing import List, Optional

import arrow
import attrdict
import yaml

from .dirs import USER_CONFIG_DIR, V10LEGACY_USER_CONFIG_DIR
from .koudai import VOD
from .utils import extension_from_url, sanitize_filename


if os.path.exists(os.path.expanduser("~/.config/kvm48/config.yml")):
    # Legacy config path is respected.
    DEFAULT_CONFIG_DIR = os.path.normcase(os.path.expanduser("~/.config/kvm48/"))
else:
    DEFAULT_CONFIG_DIR = USER_CONFIG_DIR
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_DIR, "config.yml")
DEFAULT_FILTER_DIR = os.path.join(DEFAULT_CONFIG_DIR, "filters")
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
#named_subdirs: off

# Editor to use when a text editor is needed (e.g. in perf mode). Either
# a command name or an absolute path. If not provided, OS-dependent
# fallbacks will be used.
#
# Options required by the editor command can be further specified in
# editor_opts, which is a sequence.
#
# Note that the editor must be blocking, i.e., only returns control when
# the file is saved and the editor is explicitly closed.
#
# *nix example:
#
#   editor: vim
#
# Windows example:
#
#   editor: notepad++
#   editor_opts: ['-multiInst', '-notabbar', '-nosession']
#
# Note: If Notepad++ is installed via Chocolatey, the notepad++
# executable in Chocolatey's bin is actually a non-blocking wrapper and
# not suitable as KVM48's editor. Specify the actual path of
# notepad++.exe instead, e.g., C:\\Program Files\\Notepad++\\notepad++.
#
# New in v1.0.
#
#editor:
#editor_opts:

# Whether to allow daily update checks for KVM48. Default is on.
# update_checks: on

# Perf mode specific settings (--mode perf).
#
# New in v1.0.
perf:
  # Perf mode verrides (defaults to corresponding global settings).

  #group_id:

  #span:

  #directory:

  # In perf mode, if named_subdirs is on, subdirectories are named after
  # titles of stages, e.g., 美丽48区. Note however that since in perf
  # mode users are prompted to review the download list and manually
  # edit the paths as they see fit, this setting only affects the
  # recommended paths and can be manually overridden.
  #named_subdirs:

  # Whether to show instructions text in perf mode interactively editor.
  # Default is on.
  #instructions: off
"""
FILTER_TEMPLATE = """\
# This module is imported to preprocess and exclude filenames/filepaths
# of VODS in perf mode.
#
# A single function named `filter` with the signature
#
#   (str,) -> Optional[str]
#
# is expected. The default filename/filepath derived from the title and
# subtitle of a VOD is passed to the `filter` function. If the return
# value is a string, it is used as the filename/filepath instead. If the
# return value is `None`, the VOD is considered excluded and
# automatically commented out (it can still be restored during
# interactive editing).
#
# An example is given below.
#
#
#import re
#
#RE = re.compile
#IGNORES = [RE(r"生日会")]
#SUBS = [
#    # (pattern, repl)
#    (RE(r"(S|N|H|X)II"), r"\\1Ⅱ"),
#    (RE(r"Team Ft", re.I), r"Team Ft"),
#    (RE(r"Team", re.I), r"Team"),
#    (RE(r"\s+"), r" "),
#]
#
#def filter(path):
#    for pattern in IGNORES:
#        if pattern.search(path):
#            return None
#    for pattern, repl in SUBS:
#        path = pattern.sub(repl, path)
#    return path
"""


def default_filter_file(mode: str) -> str:
    return os.path.join(DEFAULT_FILTER_DIR, "%s.py" % mode)


DEFAULT_FILTER = lambda path, **kwargs: path


class ConfigError(Exception):
    pass


class Config(object):
    def __init__(self):
        self.mode = "std"  # type: str
        self._group_id = 0  # type: int
        self.names = []  # type: List[str]
        self._span = 1  # type: int
        self._directory = None  # type: str
        self.naming = DEFAULT_NAMING_PATTERN  # type: str
        self._named_subdirs = False  # type: bool
        self.editor = None  # type: str
        self.editor_opts = None  # type: List[str]
        self.update_checks = True  # type: bool
        self._perf = dict()  # type: Dict[str, Any]
        self._perf_group_id = 0  # type: int
        self._perf_span = 1  # type: int
        self._perf_directory = None  # type: str
        self._perf_named_subdirs = False  # type: bool
        self.perf_instructions = True  # type: bool

        self._std_filter = DEFAULT_FILTER  # type: Callable
        self._perf_filter = DEFAULT_FILTER  # type: Callable

    def load(self, config_file: str = None) -> None:
        if not config_file:
            config_file = DEFAULT_CONFIG_FILE
        try:
            with open(config_file, encoding="utf-8") as fp:
                obj = yaml.load(fp.read())
        except Exception as exc:
            raise ConfigError("failed to load/parse %s: %s" % (config_file, str(exc)))

        try:
            self._group_id = int(obj.get("group_id") or 0)
        except ValueError:
            raise ConfigError("invalid group_id; must be an integer")
        if self._group_id not in (0, 10, 11, 12, 13, 14):
            raise ConfigError(
                "unrecognized group_id; must be one of 0, 10, 11, 12, 13, and 14"
            )

        self.names = obj["names"]
        if not isinstance(self.names, list) or not all(
            isinstance(v, str) for v in self.names
        ):
            raise ConfigError("invalid names; names must be a nonempty list of strings")

        try:
            self._span = max(int(obj.get("span") or 1), 1)
        except ValueError:
            raise ConfigError("invalid span; must be an integer")

        directory = obj.get("directory")
        if directory:
            directory = os.path.abspath(os.path.expanduser(directory))
            if not os.path.isdir(directory):
                raise ConfigError("nonexistent directory: %s" % directory)
            self._directory = directory
        else:
            self._directory = os.getcwd()

        self.naming = obj.get("naming") or DEFAULT_NAMING_PATTERN
        self.test_naming_pattern()

        self._named_subdirs = obj.get("named_subdirs", False)
        if not isinstance(self._named_subdirs, bool):
            raise ConfigError("invalid named_subdirs; named_subdirs must be a boolean")

        self.editor = obj.get("editor")
        if not self.editor:
            self.editor = None
        else:
            if not isinstance(self.editor, str):
                raise ConfigError("invalid editor; editor must be a string")

        self.editor_opts = obj.get("editor_opts")
        if not self.editor_opts:
            self.editor_opts = None
        else:
            if not isinstance(self.editor_opts, list) or any(
                not isinstance(opt, str) for opt in self.editor_opts
            ):
                raise ConfigError(
                    "invalid editor_opts; editor_opts must be a sequence of strings"
                )

        self.update_checks = obj.get("update_checks", True)
        if not isinstance(self.update_checks, bool):
            raise ConfigError("invalid update_checks; update_checks must be a boolean")

        self._perf = obj.get("perf") or dict()
        if not isinstance(self._perf, dict):
            raise ConfigError("invalid perf section; perf must be a dict")

        self._perf_directory = os.path.abspath(
            os.path.expanduser(self._perf.get("directory") or self._directory)
        )
        if not os.path.isdir(self._perf_directory):
            raise ConfigError("nonexistent perf.directory: %s" % self._perf_directory)

        try:
            self._perf_span = max(int(self._perf.get("span") or self._span), 1)
        except ValueError:
            raise ConfigError("invalid perf.span; must be an integer")

        try:
            self._perf_group_id = int(self._perf.get("group_id") or self._group_id)
        except ValueError:
            raise ConfigError("invalid group_id; must be an integer")
        if self._perf_group_id not in (0, 10, 11, 12, 13, 14):
            raise ConfigError(
                "unrecognized perf.group_id; must be one of 0, 10, 11, 12, 13, and 14"
            )

        self._perf_named_subdirs = self._perf.get("named_subdirs", self._named_subdirs)
        if not isinstance(self._perf_named_subdirs, bool):
            raise ConfigError("invalid perf.named_subdirs; must be a boolean")

        self.perf_instructions = self._perf.get("instructions", True)
        if not isinstance(self.perf_instructions, bool):
            raise ConfigError("invalid perf.instructions; must be a boolean")

    # If `file` is None, the filter is loaded from the default location.
    # If `file` is the empty string, the filter is reset to identity.
    # Otherwise, the filter is loaded from `file`.
    def load_filter(self, mode: str, file: Optional[str]) -> None:
        if mode not in ["std", "perf"]:
            raise ValueError("unrecognized mode %s" % repr(mode))
        if file == "":
            return DEFAULT_FILTER
        if file is None:
            file = default_filter_file(mode)
        try:
            spec = importlib.util.spec_from_file_location("user_filter_%s" % mode, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            filter = module.filter
        except Exception:
            filter = DEFAULT_FILTER
        setattr(self, "_%s_filter" % mode, filter)

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
        sys.stderr.write(
            "Configuration template written to %s.\n" % DEFAULT_CONFIG_FILE
            + "Please edit the file to suit your needs before using kvm48.\n\n"
        )
        if V10LEGACY_USER_CONFIG_DIR is not None:
            sys.stderr.write(
                "If you had a config file and just upgraded to v1.1, "
                "note that the config location has changed, and please "
                "move %s to %s.\n\n" % (V10LEGACY_USER_CONFIG_DIR, DEFAULT_CONFIG_DIR)
            )

    @staticmethod
    def dump_filter_template():
        if not os.path.isdir(DEFAULT_FILTER_DIR):
            os.makedirs(DEFAULT_FILTER_DIR, mode=0o700)
        filter_file = default_filter_file("perf")
        if os.path.isfile(filter_file) and os.stat(filter_file).st_size > 0:
            return
        with open(filter_file, "w", encoding="utf-8") as fp:
            fp.write(FILTER_TEMPLATE)
        sys.stderr.write("Filter template written to %s.\n" % filter_file)

    @property
    def group_id(self) -> int:
        if self.mode == "std":
            return self._group_id
        elif self.mode == "perf":
            return self._perf_group_id
        else:
            raise ConfigError("unrecognized mode %s" % repr(self.mode))

    @property
    def span(self) -> int:
        if self.mode == "std":
            return self._span
        elif self.mode == "perf":
            return self._perf_span
        else:
            raise ConfigError("unrecognized mode %s" % repr(self.mode))

    @property
    def directory(self) -> str:
        if self.mode == "std":
            return self._directory
        elif self.mode == "perf":
            return self._perf_directory
        else:
            raise ConfigError("unrecognized mode %s" % repr(self.mode))

    @property
    def named_subdirs(self) -> bool:
        if self.mode == "std":
            return self._named_subdirs
        elif self.mode == "perf":
            return self._perf_named_subdirs
        else:
            raise ConfigError("unrecognized mode %s" % repr(self.mode))

    @property
    def group_name(self) -> str:
        return self._get_group_name(self.group_id)

    def filename(self, vod: VOD) -> str:
        if hasattr(vod, "filename") and vod.filename:
            return vod.filename
        unsanitized = self.naming % {
            "date": vod.start_time.strftime("%Y-%m-%d"),
            "date_c": vod.start_time.strftime("%Y%m%d"),
            "datetime": vod.start_time.strftime("%Y-%m-%d %H.%M.%S"),
            "datetime_c": vod.start_time.strftime("%Y%m%d%H%M%S"),
            "id": vod.id,
            "name": vod.name,
            "type": vod.type,
            "title": vod.title.strip(),
            "ext": extension_from_url(vod.vod_url),
        }
        return sanitize_filename(unsanitized)

    def filepath(self, vod: VOD) -> str:
        if hasattr(vod, "filepath") and vod.filepath:
            return vod.filepath
        if self.named_subdirs and hasattr(vod, "name"):
            return sanitize_filename(vod.name or "其它") + os.sep + self.filename(vod)
        else:
            return self.filename(vod)

    def filter(self, path: str) -> Optional[str]:
        if self.mode == "std":
            filter_func = self._std_filter
        elif self.mode == "perf":
            filter_func = self._perf_filter
        else:
            raise ConfigError("unrecognized mode %s" % repr(self.mode))
        try:
            return filter_func(path)
        except Exception:
            return path

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
    def _get_group_name(group_id: int) -> str:
        if group_id == 0:
            return "48G"
        elif group_id == 10:
            return "SNH48"
        elif group_id == 11:
            return "BEJ48"
        elif group_id == 12:
            return "GNZ48"
        elif group_id == 13:
            return "SHY48"
        elif group_id == 14:
            return "CKG48"
        else:
            raise ValueError("unrecognized group id %d" % group_id)
