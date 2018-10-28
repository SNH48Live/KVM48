import os
import subprocess
import sys


def launch_editor(file: str) -> None:
    if os.name == "nt":
        try:
            os.startfile(file, "edit")
            return
        except OSError:
            # OSError is raised when file extension has no association.
            # In that case, just launch Notepad.
            #
            # https://docs.microsoft.com/en-us/windows/desktop/procthread/process-creation-flags
            # 0x00000008 DETACHED_PROCESS
            # 0x00000200 CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(["notepad", file], creationflags=0x00000008 | 0x00000200)
        return
    editor = os.getenv("VISUAL") or os.getenv("EDITOR")
    if editor:
        try:
            subprocess.call([editor, file])
            return
        except FileNotFoundError:
            pass
    for fallback_editor in ("nano", "vim", "vi"):
        try:
            subprocess.call([fallback_editor, file])
            return
        except FileNotFoundError:
            pass
    sys.stderr.write("[ERROR] cannot find an editor to edit '%s'" % file)
