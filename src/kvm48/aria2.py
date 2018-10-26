import os
import subprocess
import sys
from typing import List, Optional, Tuple

# Override some bad defaults.
ARIA2C_OPTS = [
    "--max-connection-per-server=16",
    "--allow-overwrite=false",
    "--auto-file-renaming=false",
    "--check-certificate=false",
    "--remote-time=true",
]


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
            if os.path.exists(filepath) and not os.path.exists(filepath + ".aria2"):
                continue
            filedir = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            print(url, file=fp)
            if filedir:
                print("\tdir=%s" % filedir, file=fp)
            print("\tout=%s" % filename, file=fp)
            written_targets.append(target)
    return written_targets


# The return value is the exit status of aria2.
def download(manifest: str) -> int:
    args = ["aria2c", *ARIA2C_OPTS, "--input-file", manifest]
    print(" ".join(args), file=sys.stderr)
    try:
        return subprocess.call(args)
    except FileNotFoundError:
        raise RuntimeError("aria2c(1) not found")
