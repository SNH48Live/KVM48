import atexit
import os
import sys

import psutil

from .dirs import USER_CACHE_DIR


PIDFILE = os.path.join(USER_CACHE_DIR, "kvm48.pid")


def lock_to_one_instance():
    if os.path.exists(PIDFILE):
        try:
            with open(PIDFILE, encoding="utf-8") as fp:
                pid = int(fp.read().strip())
            if psutil.pid_exists(pid):
                sys.stderr.write(
                    "[CRITICAL] another instance of kvm48 is already running (pid %d)\n"
                    % pid
                )
                sys.exit(1)
        except Exception:
            pass

    atexit.register(os.unlink, PIDFILE)
    try:
        os.makedirs(USER_CACHE_DIR, exist_ok=True)
        with open(PIDFILE, "w", encoding="utf-8") as fp:
            fp.write(str(os.getpid()))
    except Exception:
        pass
