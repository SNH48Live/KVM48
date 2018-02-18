import os
import sys
import tempfile
from typing import List, Tuple

# Override some bad defaults.
ARIA2C_OPTS = [
    '--max-connection-per-server=16',
    '--allow-overwrite=false',
    '--auto-file-renaming=false',
    '--check-certificate=false',
]


# targets is a list of (url, filename) pairs.
def download(targets: List[Tuple[str, str]], *, directory: str = None):
    def existing_file_filter(target: Tuple[str, str]) -> bool:
        url, filename = target
        path = os.path.join(directory, filename) if directory else filename
        if os.path.exists(path) and not os.path.exists(path + '.aria2'):
            print("'%s' already exists" % path, file=sys.stderr)
            return False  # File exists, filter this out
        else:
            return True

    targets = list(filter(existing_file_filter, targets))

    args = ['aria2c'] + ARIA2C_OPTS
    if directory:
        args.append('--dir=%s' % directory)
    fd, path = tempfile.mkstemp(prefix='kvm48.', suffix='.aria2in')
    with os.fdopen(fd, 'w') as fp:
        for url, filename in targets:
            print(url, file=fp)
            print('\tout=%s' % filename, file=fp)
    args.extend(['--input-file', path])
    print(' '.join(args), file=sys.stderr)
    try:
        os.execvp('aria2c', args)
    except FileNotFoundError:
        raise RuntimeError('aria2c(1) not found')
