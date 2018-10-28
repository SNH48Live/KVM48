import os
import subprocess
import sys
from typing import List, Tuple

from distlib.version import NormalizedVersion, UnsupportedVersionError


# v1.0b1: --exist-ok
MINIMUM_CATERPILLAR_VERSION = "1.0b1"


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
            sys.stderr.write(
                "\n[ERROR] caterpillar(1) not found; see https://github.com/zmwangx/caterpillar\n"
            )
        return False
    except subprocess.CalledProcessError:
        if warn:
            sys.stderr.write("\n[ERROR] caterpillar --version failed\n")
        return False
    try:
        version = NormalizedVersion(pep440ify(raw_version))
    except UnsupportedVersionError:
        if warn:
            sys.stderr.write(
                "\n[WARNING] failed to recognize caterpillar version %s; "
                "upgrade to at least v%s if you run into problems\n"
                % (repr(raw_version), MINIMUM_CATERPILLAR_VERSION)
            )
        # Fingers crossed
        return True
    if version < NormalizedVersion(MINIMUM_CATERPILLAR_VERSION):
        if warn:
            sys.stderr.write(
                "\n[ERROR] caterpillar version %s is too low; "
                "please upgrade to at least v%s\n"
                % (raw_version, MINIMUM_CATERPILLAR_VERSION)
            )
        return False
    return True


# Returns the list of targets that are actually written (not already
# downloaded).
def write_manifest(
    targets: List[Tuple[str, str]], path: str, *, target_directory: str = None
) -> List[Tuple[str, str]]:
    written_targets = []
    with open(path, "w", encoding="utf-8") as fp:
        for target in targets:
            url, filepath = target
            filepath = (
                os.path.join(target_directory, filepath)
                if target_directory
                else filepath
            )
            if os.path.exists(filepath):
                continue
            print("%s\t%s" % (url, filepath), file=fp)
            written_targets.append(target)
    return written_targets


# The return value is the exit status of aria2.
def download(manifest: str) -> int:
    args = ["caterpillar", "--batch", "--exist-ok", manifest]
    print(" ".join(args), file=sys.stderr)
    try:
        return subprocess.call(args)
    except FileNotFoundError:
        raise RuntimeError("caterpillar(1) not found")
