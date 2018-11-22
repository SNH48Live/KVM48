import os
import subprocess
import sys
from typing import List


def nt_popen(args: List[str]):
    # https://docs.microsoft.com/en-us/windows/desktop/procthread/process-creation-flags
    # 0x00000008 DETACHED_PROCESS
    # 0x00000200 CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(args, creationflags=0x00000008 | 0x00000200)


def call_and_warn_return_code(args: List[str]):
    code = subprocess.call(args)
    if code != 0:
        sys.stderr.write("[WARNING] %s exited with code %d\n" % (args[0], code))


def launch_editor(
    file: str,
    *,
    editor: str = None,
    opts: List[str] = None,
    blocking: bool = False,
    raise_: bool = False
) -> None:
    if editor:
        if opts is None:
            opts = []
        try:
            if os.name == "nt" and not blocking:
                nt_popen([editor, *opts, file])
            else:
                call_and_warn_return_code([editor, *opts, file])
            return
        except FileNotFoundError:
            sys.stderr.write("[WARNING] cannot find editor '%s'" % editor)

    if os.name == "nt":
        if blocking:
            call_and_warn_return_code(["notepad", file])
        else:
            try:
                os.startfile(file, "edit")
            except OSError:
                # OSError is raised when file extension has no association.
                # In that case, just launch Notepad.
                nt_popen(["notepad", file])
        return

    editor = os.getenv("VISUAL") or os.getenv("EDITOR")
    if editor:
        try:
            call_and_warn_return_code([editor, file])
            return
        except FileNotFoundError:
            pass
    for fallback_editor in ("nano", "vim", "vi"):
        try:
            call_and_warn_return_code([fallback_editor, file])
            return
        except FileNotFoundError:
            pass
    if raise_:
        raise RuntimeError("cannot find an editor to edit '%s'" % file)
    else:
        sys.stderr.write("[ERROR] cannot find an editor to edit '%s'" % file)
