import os
import subprocess
import sys
import tempfile
from typing import List, Optional, Tuple

# Override some bad defaults.
ARIA2C_OPTS = [
    "--max-connection-per-server=16",
    "--allow-overwrite=false",
    "--auto-file-renaming=false",
    "--check-certificate=false",
    "--remote-time=true",
]


# targets is a list of (url, filename) pairs.
#
# If execvp is False or the underlying OS is Windows NT, execute aria2c
# in a subprocess; otherwise, replace the process with execvp.
#
# If aria2c is run in a subprocess, the return code is returned.
def download(
    targets: List[Tuple[str, str]], *, directory: str = None, execvp: bool = False
) -> Optional[int]:
    def existing_file_filter(target: Tuple[str, str]) -> bool:
        url, filename = target
        path = os.path.join(directory, filename) if directory else filename
        if os.path.exists(path) and not os.path.exists(path + ".aria2"):
            print("'%s' already exists" % path, file=sys.stderr)
            return False  # File exists, filter this out
        else:
            return True

    targets = list(filter(existing_file_filter, targets))

    if not targets:
        print("No files to download.", file=sys.stderr)
        return 0

    args = ["aria2c"] + ARIA2C_OPTS
    if directory:
        args.append("--dir=%s" % directory)
    fd, path = tempfile.mkstemp(prefix="kvm48.", suffix=".aria2in")
    with os.fdopen(fd, "w", encoding="utf-8") as fp:
        for url, filename in targets:
            print(url, file=fp)
            print("\tout=%s" % filename, file=fp)
    args.extend(["--input-file", path])
    print(" ".join(args), file=sys.stderr)
    try:
        if execvp and os.name != "nt":
            os.execvp("aria2c", args)
        else:
            return subprocess.call(args)
    except FileNotFoundError:
        raise RuntimeError("aria2c(1) not found")
