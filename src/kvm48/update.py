import datetime
import os
import sys
import textwrap
import time
from typing import Optional

import requests

from .dirs import USER_CACHE_DIR
from .version import __version__


LAST_CHECK_FILE = os.path.join(USER_CACHE_DIR, "last_check.txt")


def load_last_check_date() -> Optional[datetime.date]:
    try:
        with open(LAST_CHECK_FILE, encoding="utf-8") as fp:
            return datetime.date.fromisoformat(fp.read().strip())
    except Exception:
        return None


def write_last_check_date() -> None:
    try:
        os.makedirs(USER_CACHE_DIR, exist_ok=True)
        with open(LAST_CHECK_FILE, "w", encoding="utf-8") as fp:
            fp.write(str(datetime.date.today()))
    except Exception:
        return None


def pip_upgrade_command(prerelease: bool = False) -> str:
    args = ["pip3", "install", "-U", *(["--pre"] if prerelease else []), "KVM48"]
    return " ".join(args)


def check_update(force: bool = False) -> None:
    if not force:
        last_check_date = load_last_check_date()
        if datetime.date.today() == last_check_date:
            return
        write_last_check_date()
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

                    The program will resume in 5 seconds...
                    """.format(
                        new_version=new_version,
                        current_version=__version__,
                        pip_upgrade_command=pip_upgrade_command(prerelease=prerelease),
                    )
                )
            )
            time.sleep(5)
        else:
            sys.stderr.write("KVM48 is up-to-date.\n")
    except Exception:
        pass
