import os
import subprocess
import sys
from typing import Optional

from distlib.version import NormalizedVersion, UnsupportedVersionError


# v1.0b1: --exist-ok
# v1.0b2: --remove-manifest-on-success
MINIMUM_CATERPILLAR_VERSION = "1.0b2"


# Transform my cavalier version numbers for PEP-440 compilance.
# That is, I can't just slap dev onto any non-dev version; I need .devN.
def pep440ify(version_string: str) -> str:
    if version_string.endswith("dev") and not version_string.endswith(".dev"):
        return version_string[:-3] + ".dev1"
    elif version_string.endswith(".dev"):
        return version_string + "1"
    else:
        return version_string


def check_caterpillar_requirement(warn: bool = True) -> bool:
    try:
        raw_version = (
            subprocess.check_output(
                ["caterpillar", "--version"], stderr=subprocess.DEVNULL
            )
            .decode("utf-8")
            .strip()
        )
    except FileNotFoundError:
        if warn:
            print(
                "[ERROR] caterpillar(1) not found; see https://github.com/zmwangx/caterpillar.",
                file=sys.stderr,
            )
        return False
    except subprocess.CalledProcessError:
        if warn:
            print("[ERROR] caterpillar --version failed", file=sys.stderr)
        return False
    try:
        version = NormalizedVersion(pep440ify(raw_version))
    except UnsupportedVersionError:
        if warn:
            print(
                "[WARNING] failed to recognize caterpillar version %s; "
                "upgrade to at least v%s if you run into problems"
                % (repr(raw_version), MINIMUM_CATERPILLAR_VERSION),
                file=sys.stderr,
            )
        # Fingers crossed
        return True
    if version < NormalizedVersion(MINIMUM_CATERPILLAR_VERSION):
        if warn:
            print(
                "[ERROR] caterpillar version %s is too low; "
                "please upgrade to at least v%s"
                % (raw_version, MINIMUM_CATERPILLAR_VERSION),
                file=sys.stderr,
            )
        return False
    return True


# execvp: see aria2.download.
def download(batch_manifest: str, execvp: bool = False) -> Optional[int]:
    args = [
        "caterpillar",
        "--batch",
        "--exist-ok",
        "--remove-manifest-on-success",
        batch_manifest,
    ]
    print(" ".join(args), file=sys.stderr)
    try:
        if execvp and os.name != "nt":
            os.execvp("caterpillar", args)
        else:
            return subprocess.call(args)
    except FileNotFoundError:
        raise RuntimeError("caterpillar(1) not found")
