"""Follow the game's debug log, like Get-Content -Tail 30 -Wait."""
from collections import deque
import sys
import time

from . import settings
from .release_archive import ReleaseError


def follow(path=None, tail=30, interval=0.5, out=sys.stdout):
    try:
        path = path or settings.debug_log()
    except LookupError as error:
        raise ReleaseError(str(error)) from None
    print(f'Following {path} (Ctrl+C to stop)', file=out, flush=True)
    with open(path, encoding='utf-8', errors='replace', newline='') as log:
        for line in deque(log, maxlen=tail):
            out.write(line)
        out.flush()
        while True:
            line = log.readline()
            if line:
                out.write(line)
                out.flush()
                continue
            time.sleep(interval)
            # The game truncates the log on start; reopen from the top when it shrinks.
            if path.stat().st_size < log.tell():
                log.seek(0)
