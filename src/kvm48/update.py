import datetime
import os
import sys
import textwrap
import time
from typing import Optional, Tuple

import requests
from distlib.version import NormalizedVersion, UnsupportedVersionError

from .dirs import USER_CACHE_DIR
from .utils import read_keypress_with_timeout
from .version import __version__


LAST_CHECK_FILE = os.path.join(USER_CACHE_DIR, "last_check.txt")

# v1.3
WHATS_NEW = """\
This release introduces new command line and config options, in addition \
to improvements and bug fixes.

- New command line option -M, --multiple-instance allows multiple \
simultaneous instances of kvm48 (use with causion).

- New command line option --dump-config-template dumps the latest \
configuration file template.

- New configuration option convert_non_bmp_chars to enable replacement \
or removal of non-BMP characters (code points above U+FFFF, e.g. most \
emojis) in filenames for compatibility with legacy filesystems with \
only UCS-2 support, e.g., FAT32.

- List of successfully downloaded files is now printed at the end of \
each session.

- The `names` config option is no longer required when running in perf \
mode.
"""


def load_last_check_info() -> Tuple[Optional[datetime.date], Optional[str]]:
    try:
        with open(LAST_CHECK_FILE, encoding="utf-8") as fp:
            date = datetime.date.fromisoformat(fp.readline().strip())
            version = fp.readline().strip() or None
            return (date, version)
    except Exception:
        return (None, None)


def write_last_check_info() -> None:
    try:
        os.makedirs(USER_CACHE_DIR, exist_ok=True)
        with open(LAST_CHECK_FILE, "w", encoding="utf-8") as fp:
            print(datetime.date.today(), file=fp)
            print(__version__, file=fp)
    except Exception:
        return None


def pip_upgrade_command(prerelease: bool = False) -> str:
    args = ["pip3", "install", "-U", *(["--pre"] if prerelease else []), "KVM48"]
    return " ".join(args)


def check_update_or_print_whats_new(force: bool = False) -> None:
    last_check_date, last_check_version = load_last_check_info()
    write_last_check_info()

    # Only print what's new when the program has checked for updates in
    # the past, and the version that last checked for updates is older
    # than the current running version, and the current running version
    # is not a dev version. Filters out new installations.
    print_whats_new = True
    if not last_check_date:
        print_whats_new = False
    if "dev" in __version__:
        print_whats_new = False
    try:
        if NormalizedVersion(last_check_version) >= NormalizedVersion(__version__):
            print_whats_new = False
    except UnsupportedVersionError:
        pass

    if print_whats_new:
        sys.stderr.write("WHAT'S NEW IN KVM48 v%s:\n\n" % __version__)
        sys.stderr.write(WHATS_NEW)
        sys.stderr.write(
            "\nPress any key to continue (the program will auto-resume in 15 seconds)...\n\n"
        )
        read_keypress_with_timeout(15)

    if not force and datetime.date.today() == last_check_date:
        return
    sys.stderr.write("Checking for updates for KVM48...\n")
    try:
        r = requests.get(
            "https://v.tcl.sh/pypi/KVM48/new_version",
            params=dict(current_version=__version__),
            timeout=5,
        )
        resp = r.json()
        new_version = resp.get("new_version")
        prerelease = resp.get("is_prerelease")
        if new_version is not None:
            sys.stderr.write(
                textwrap.dedent(
                    """\
                    KVM48 {new_version} is available. You are running version {current_version}. You can upgrade with command

                        {pip_upgrade_command}

                    Press any key to continue (the program will auto-resume in 5 seconds)...

                    """.format(
                        new_version=new_version,
                        current_version=__version__,
                        pip_upgrade_command=pip_upgrade_command(prerelease=prerelease),
                    )
                )
            )
            read_keypress_with_timeout(5)
        else:
            sys.stderr.write("KVM48 is up-to-date.\n")
    except Exception:
        pass
